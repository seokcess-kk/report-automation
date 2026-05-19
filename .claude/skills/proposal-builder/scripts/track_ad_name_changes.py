"""광고명 변경 추적 - 3개 데이터 소스를 합쳐 시계열 변천사를 복원.

(1) 스냅샷 시계열 (output/data/YYYYMMDD/parsed.parquet, git 보존)
    - 매일 자동 커밋된 일별 스냅샷 비교
    - 같은 ad_id의 canonical_name (= _off 제거한 정규화 이름) 이 바뀐 시점 추출
    - TikTok 자체 API는 변경 전 이름을 보존하지 않지만, 이 스냅샷에는 보존됨

(2) 현재 raw report 내부 (input/tiktok_raw.csv)
    - 같은 ad_id의 ad_name 이 일자별로 다른 케이스 - TikTok Ads Manager 수정이 raw 에도 반영된 경우

(3) API meta vs raw 마지막 불일치 (input/tiktok_ad_meta.csv)
    - raw 마지막 일자 이후에 광고가 수정·재활용된 케이스 - modify_time 으로 정확한 변경 시점 확인

분류:
    - real_changes: canonical_name 이 바뀐 진짜 이름 수정 (오타 수정·재활용 등)
    - off_toggles: _off 접미사만 토글된 케이스 (운영 ON/OFF 변경) - 카운트만, 별도 저장 안 함

추적이 필요한 이유:
    - 매칭키(소재유형_소재명) 기반 집계에서 같은 ad_id 의 성과가 두 매칭키로 흩어질 위험
    - 광고 재활용 케이스는 분석 정확도에 영향 (소재유형까지 완전히 달라지는 경우 있음)
"""
import re
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


SNAPSHOT_ROOT = Path('output/data')
RAW_CSV_DEFAULT = 'input/tiktok_raw.csv'
META_CSV_DEFAULT = 'input/tiktok_ad_meta.csv'
OFF_SUFFIX = re.compile(r'_off$', re.IGNORECASE)


def canonical(name) -> str:
    """_off 접미사를 제거한 정규화 이름."""
    if name is None or (isinstance(name, float) and pd.isna(name)) or not name:
        return ''
    return OFF_SUFFIX.sub('', str(name))


def build_snapshot_timeline() -> tuple[dict[str, list], int]:
    """모든 스냅샷을 시계열로 합쳐 ad_id 별 (snapshot_date, ad_name) 시퀀스를 구성.

    한 스냅샷 × ad_id 에 여러 ad_name 이 보이면 (raw 내부 변경) 행수가 가장 많은 이름을 채택.
    스냅샷 간 변천만 깨끗하게 잡기 위함. raw 내부 변경은 detect_raw_internal_changes() 가 별도 추적.

    Returns:
        (by_id, n_snaps): ad_id 별 시간순 [(snapshot_date, ad_name), ...]
    """
    snaps = sorted(SNAPSHOT_ROOT.glob('2026*/parsed.parquet'))
    by_id = {}
    for snap in snaps:
        snap_date = snap.parent.name
        try:
            df = pd.read_parquet(snap, columns=['ad_id', 'ad_name'])
        except Exception:
            continue
        df['ad_id'] = df['ad_id'].astype(str)
        df = df.dropna(subset=['ad_id', 'ad_name'])
        # 한 스냅샷에서 같은 ad_id 가 여러 이름을 가지면 - 행수가 가장 많은 1개로 압축
        counts = df.groupby(['ad_id', 'ad_name']).size().reset_index(name='n')
        top = counts.sort_values(['ad_id', 'n'], ascending=[True, False]).drop_duplicates('ad_id', keep='first')
        for _, row in top.iterrows():
            by_id.setdefault(row['ad_id'], []).append((snap_date, str(row['ad_name'])))
    for ad_id in by_id:
        by_id[ad_id].sort()
    return by_id, len(snaps)


def extract_changes_from_timeline(timeline: dict[str, list]) -> tuple[list[dict], list[dict]]:
    """ad_id 별 시계열에서 변경 이벤트 추출.

    real_changes: canonical_name 이 바뀐 시점 (실제 이름 수정)
    off_toggles: canonical_name 은 같지만 _off 접미사가 토글된 시점
    """
    real_changes = []
    off_toggles = []

    for ad_id, seq in timeline.items():
        prev_name = None
        prev_canon = None
        first_seen_date = None
        for snap_date, name in seq:
            canon = canonical(name)
            if prev_name is None:
                first_seen_date = snap_date
                prev_name = name
                prev_canon = canon
                continue
            if name == prev_name:
                continue  # 변화 없음
            if canon == prev_canon:
                # _off 만 토글
                off_toggles.append({
                    'ad_id': ad_id,
                    'first_seen_date': first_seen_date,
                    'snapshot_date': snap_date,
                    'before': prev_name,
                    'after': name,
                })
            else:
                real_changes.append({
                    'ad_id': ad_id,
                    'first_seen_date': first_seen_date,
                    'snapshot_date': snap_date,
                    'before': prev_name,
                    'after': name,
                    'change_type': _classify_change_type(prev_canon, canon),
                })
            prev_name = name
            prev_canon = canon

    return real_changes, off_toggles


def _classify_change_type(before_canon: str, after_canon: str) -> str:
    """이름 수정의 성격을 자동 분류."""
    b_parts = before_canon.split('_')
    a_parts = after_canon.split('_')
    if len(b_parts) < 4 or len(a_parts) < 4:
        return 'other'
    if b_parts[0] != a_parts[0]:
        return 'creative_kind'  # (신)/(재) 등 소재구분 변경
    if b_parts[1] != a_parts[1]:
        return 'branch'         # 지점 변경
    if b_parts[2] != a_parts[2]:
        return 'ad_type'        # 소재유형 변경
    # 날짜코드 (마지막 토큰) 비교
    if b_parts[-1] != a_parts[-1]:
        # 소재명 동일 + 날짜코드만 다르면 → 오타/재가공
        if b_parts[3:-1] == a_parts[3:-1]:
            return 'date_code'
    # 소재명 부분이 다르면
    if b_parts[3:-1] != a_parts[3:-1]:
        return 'creative_name'
    return 'other'


def detect_raw_internal_changes(raw_csv_path: str) -> list[dict]:
    """현재 raw CSV 내부에서 같은 ad_id 가 일자별로 다른 ad_name 을 가진 케이스."""
    raw = pd.read_csv(raw_csv_path, encoding='utf-8-sig', dtype={'광고 ID': str})
    raw = raw.rename(columns={'광고 ID': 'ad_id', '광고 이름': 'ad_name', '일별': 'date'})
    raw['date'] = pd.to_datetime(raw['date'])

    name_counts = raw.groupby('ad_id')['ad_name'].nunique()
    multi_ids = name_counts[name_counts > 1].index.tolist()

    events = []
    for ad_id in multi_ids:
        sub = raw[raw['ad_id'] == ad_id].sort_values('date')
        prev_name = None
        for _, row in sub.iterrows():
            if prev_name is not None and row['ad_name'] != prev_name:
                events.append({
                    'ad_id': ad_id,
                    'change_date': row['date'].strftime('%Y-%m-%d'),
                    'before': prev_name,
                    'after': row['ad_name'],
                })
            prev_name = row['ad_name']
    return events


def detect_meta_mismatches(raw_csv_path: str, meta_csv_path: str) -> list[dict]:
    """API meta 의 ad_name 과 raw 마지막 ad_name 이 다른 케이스 (raw 이후 수정·재활용)."""
    raw = pd.read_csv(raw_csv_path, encoding='utf-8-sig', dtype={'광고 ID': str})
    raw = raw.rename(columns={'광고 ID': 'ad_id', '광고 이름': 'ad_name', '일별': 'date'})
    raw['date'] = pd.to_datetime(raw['date'])

    try:
        meta = pd.read_csv(meta_csv_path, encoding='utf-8-sig', dtype={'ad_id': str})
    except FileNotFoundError:
        return []
    meta = meta[['ad_id', 'ad_name', 'create_time', 'modify_time']].rename(columns={'ad_name': 'meta_name'})

    raw_last = (
        raw.sort_values('date').groupby('ad_id').last()[['ad_name', 'date']]
           .reset_index().rename(columns={'ad_name': 'raw_last_name', 'date': 'raw_last_date'})
    )
    joined = meta.merge(raw_last, on='ad_id', how='inner')
    mismatch_df = joined[joined['meta_name'] != joined['raw_last_name']]

    rows = []
    for _, row in mismatch_df.iterrows():
        rows.append({
            'ad_id': row['ad_id'],
            'raw_last_date': row['raw_last_date'].strftime('%Y-%m-%d'),
            'raw_last_name': row['raw_last_name'],
            'meta_name': row['meta_name'],
            'meta_modify_time': row.get('modify_time'),
        })
    return rows


def analyze(raw_csv_path: str = RAW_CSV_DEFAULT,
            meta_csv_path: str = META_CSV_DEFAULT) -> dict:
    timeline, n_snaps = build_snapshot_timeline()
    real_changes, off_toggles = extract_changes_from_timeline(timeline)
    raw_internal = detect_raw_internal_changes(raw_csv_path)
    meta_mismatches = detect_meta_mismatches(raw_csv_path, meta_csv_path)

    # 변경 유형별 카운트
    type_counts = {}
    for c in real_changes:
        type_counts[c['change_type']] = type_counts.get(c['change_type'], 0) + 1

    return {
        'summary': {
            'snapshots_count': n_snaps,
            'ad_ids_in_timeline': len(timeline),
            'real_name_change_events': len(real_changes),
            'off_toggle_events': len(off_toggles),
            'raw_internal_change_events': len(raw_internal),
            'meta_vs_raw_mismatches': len(meta_mismatches),
            'change_type_breakdown': type_counts,
        },
        'real_changes': real_changes,
        'off_toggles': off_toggles,
        'raw_internal_changes': raw_internal,
        'meta_mismatches': meta_mismatches,
    }


def save_logs(result: dict,
              full_log_path: str = 'logs/ad_name_changes_full.csv',
              off_log_path: str = 'logs/ad_name_off_toggles.csv'):
    if result['real_changes']:
        df = pd.DataFrame(result['real_changes'])
        out = Path(full_log_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding='utf-8-sig')
        print(f"[save] {full_log_path} ({len(df)}건 - 진짜 이름 수정만)")
    else:
        print("[skip] 진짜 이름 수정 이벤트 없음")

    # off toggles 는 너무 많을 수 있어 별도 파일로
    if result['off_toggles']:
        df = pd.DataFrame(result['off_toggles'])
        out = Path(off_log_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding='utf-8-sig')
        print(f"[save] {off_log_path} ({len(df)}건 - _off 토글)")


def main():
    # Windows PowerShell cp949 환경에서 한글 출력을 위해 UTF-8 강제
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    raw = sys.argv[1] if len(sys.argv) > 1 else RAW_CSV_DEFAULT
    meta = sys.argv[2] if len(sys.argv) > 2 else META_CSV_DEFAULT
    r = analyze(raw, meta)
    s = r['summary']

    print(f"스냅샷: {s['snapshots_count']}개 / 추적 광고 ID: {s['ad_ids_in_timeline']}")
    print()
    print(f"진짜 이름 수정 이벤트:        {s['real_name_change_events']}건")
    print(f"_off 토글 이벤트:             {s['off_toggle_events']}건 (별도 분류)")
    print(f"raw 내부 일자별 변경:         {s['raw_internal_change_events']}건")
    print(f"API meta vs raw 불일치:       {s['meta_vs_raw_mismatches']}건")
    print()
    print(f"변경 유형별:")
    type_labels = {
        'date_code': '날짜코드 수정 (오타 등)',
        'creative_name': '소재명 수정',
        'ad_type': '소재유형 변경 (재활용)',
        'branch': '지점 변경',
        'creative_kind': '소재구분 변경 (신/재)',
        'other': '기타',
    }
    for k, v in s['change_type_breakdown'].items():
        print(f"  {type_labels.get(k, k)}: {v}건")

    if r['real_changes']:
        print()
        print(f"[진짜 이름 수정 이력]")
        for c in r['real_changes']:
            label = type_labels.get(c['change_type'], c['change_type'])
            print(f"  {c['ad_id']} | {c['first_seen_date']} → {c['snapshot_date']} ({label})")
            print(f"    BEFORE: {c['before']}")
            print(f"    AFTER : {c['after']}")

    if r['meta_mismatches']:
        print()
        print(f"[현재 시점 메타 vs raw 마지막 불일치 (raw 갱신 이후 광고 수정·재활용)]")
        for m in r['meta_mismatches']:
            print(f"  {m['ad_id']} (raw 마지막 {m['raw_last_date']} / meta 수정 {m['meta_modify_time']})")
            print(f"    raw : {m['raw_last_name']}")
            print(f"    meta: {m['meta_name']}")

    save_logs(r)


if __name__ == '__main__':
    main()
