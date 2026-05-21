"""타겟팅 정합성 진단 — 성별·연령 디멘션 분석 (Phase 1A)

설계 의도:
  · 다이트한의원 캠페인은 성별 타겟팅이 "여성 고정" — 즉 운영 상수
  · 검증 축: 타겟팅 의도(여성)대로 노출이 가는가 + 남성 누수 측정
  · 부가 신호: NONE(미상) 분류 전환 비중, 연령 분포 불균형

입력:
  - normalized_by_audience.parquet (ad_id × date × age_group × gender)
  - ad_id를 parsed.parquet과 join하여 지점·소재유형 부착
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES


def _extract_age_history(df: pd.DataFrame, target_age: str, target_gender: str) -> dict:
    """의도적 배제 / 한정 재운영 시점을 데이터에서 자동 추출.

    target_age 노출이 0인 주가 연속이면 '배제 기간'으로 식별.
    배제 이후 일부 지점에만 노출이 잡히면 '한정 재운영'으로 식별.
    """
    sub = df[(df['age_group'] == target_age) & (df['gender'] == target_gender)].copy()
    if sub.empty or 'date' not in sub.columns:
        return {'available': False}
    sub['date'] = pd.to_datetime(sub['date'])
    sub['week'] = sub['date'].dt.to_period('W').dt.start_time

    weekly = sub.groupby('week').agg(impr=('impressions', 'sum')).reset_index()
    weekly['exposed'] = weekly['impr'] >= 100

    # 배제 기간 — 노출 < 100인 주가 연속 2주 이상
    excluded_weeks = []
    streak_start = None
    for _, r in weekly.iterrows():
        if not r['exposed']:
            if streak_start is None:
                streak_start = r['week']
            last_zero = r['week']
        else:
            if streak_start is not None and (last_zero - streak_start).days >= 7:
                excluded_weeks.append((streak_start, last_zero))
            streak_start = None
    if streak_start is not None and (last_zero - streak_start).days >= 7:
        excluded_weeks.append((streak_start, last_zero))
    excluded_ranges = [
        {'start': s.strftime('%Y-%m-%d'), 'end': e.strftime('%Y-%m-%d')}
        for s, e in excluded_weeks
    ]

    # 첫 배제 시점 이후 ('재운영 시기') 지점 분포 — 한정 재운영 감지
    post_exclusion_branches = {}
    if excluded_weeks:
        first_exclusion_end = excluded_weeks[0][1]
        post = sub[sub['date'] > first_exclusion_end]
        if not post.empty:
            for b in sorted(post['지점'].dropna().unique()):
                bdf = post[post['지점'] == b]
                impr = int(bdf['impressions'].sum())
                clicks = int(bdf['clicks'].sum())
                conv = int(bdf['conversions'].sum())
                cost = int(bdf['cost'].sum())
                if impr >= 100:
                    post_exclusion_branches[b] = {
                        'impressions': impr,
                        'clicks': clicks,
                        'conversions': conv,
                        'cost': cost,
                        'ctr': round(clicks / impr * 100, 2) if impr else None,
                        'cvr': round(conv / clicks * 100, 2) if clicks else None,
                        'cpa': round(cost / conv) if conv else None,
                    }

    # 배제 전 (정상 운영) 지점 분포
    pre_branches = {}
    if excluded_weeks:
        first_exclusion_start = excluded_weeks[0][0]
        pre = sub[sub['date'] < first_exclusion_start]
        for b in sorted(pre['지점'].dropna().unique()):
            bdf = pre[pre['지점'] == b]
            impr = int(bdf['impressions'].sum())
            if impr >= 100:
                pre_branches[b] = {'impressions': impr}

    # 한정 재운영 식별 — 재운영 지점 수가 배제 전 지점 수의 절반 미만
    is_limited_restart = (
        len(post_exclusion_branches) > 0
        and len(pre_branches) > 0
        and len(post_exclusion_branches) <= max(1, len(pre_branches) // 2)
    )

    return {
        'available': True,
        'target_age': target_age,
        'target_gender': target_gender,
        'excluded_ranges': excluded_ranges,
        'pre_exclusion_branches': pre_branches,
        'post_exclusion_branches': post_exclusion_branches,
        'is_limited_restart': is_limited_restart,
        'restart_branches': sorted(post_exclusion_branches.keys()) if is_limited_restart else [],
        'context_note': (
            (f'{excluded_ranges[0]["start"]} ~ {excluded_ranges[-1]["end"]} 사이 {target_age} 노출이 의도적으로 배제된 기간이 있음. '
             if excluded_ranges else '')
            + (f'배제 이후 {", ".join(post_exclusion_branches.keys())} 한정으로 재운영 중. ' if is_limited_restart else '')
            + ('따라서 전 기간 합산 효율은 운영 의도(축소·한정 테스트)가 반영된 결과이며, '
               '운영 권고는 "확대 제외 + 한정 테스트 추적" 방향이 자연스러움.'
               if (excluded_ranges or is_limited_restart) else '')
        ),
    }


def _kpis(g: pd.DataFrame) -> dict:
    impr = int(g['impressions'].sum())
    clicks = int(g['clicks'].sum())
    conv = int(g['conversions'].sum())
    cost = int(g['cost'].sum())
    return {
        'impressions': impr,
        'clicks': clicks,
        'conversions': conv,
        'cost': cost,
        'ctr': round(clicks / impr * 100, 2) if impr else None,
        'cvr': round(conv / clicks * 100, 2) if clicks else None,
        'cpa': round(cost / conv) if conv else None,
    }


def analyze(audience_path: str, parsed_path: str) -> dict:
    """audience parquet + parsed.parquet → 타겟팅 정합성 진단."""
    try:
        aud = pd.read_parquet(audience_path)
    except Exception as e:
        return {'available': False, 'note': f'audience parquet 로드 실패: {e}'}

    if aud.empty:
        return {'available': False, 'note': 'audience 데이터 없음'}

    # parsed에서 지점·소재유형 가져오기 (광고별 1행만 필요)
    parsed = pd.read_parquet(parsed_path)
    parsed['ad_id'] = parsed['ad_id'].astype(str)
    aud['ad_id'] = aud['ad_id'].astype(str)
    ad_meta = (parsed[parsed['parse_status'] == 'OK']
               [['ad_id', '지점', '소재유형']]
               .drop_duplicates(subset=['ad_id'])
               .copy())

    df = aud.merge(ad_meta, on='ad_id', how='left')
    df['지점'] = df['지점'].fillna('미상')
    df['소재유형'] = df['소재유형'].fillna('미상')

    # ---- 1. 성별 분포 (전체) ----
    gender_total = {}
    for g in sorted(df['gender'].dropna().unique()):
        gender_total[str(g)] = _kpis(df[df['gender'] == g])

    total_impr = int(df['impressions'].sum())
    total_conv = int(df['conversions'].sum())

    female_impr = gender_total.get('여성', {}).get('impressions', 0)
    female_conv = gender_total.get('여성', {}).get('conversions', 0)
    male_impr = gender_total.get('남성', {}).get('impressions', 0)
    male_conv = gender_total.get('남성', {}).get('conversions', 0)
    unknown_impr = gender_total.get('미상', {}).get('impressions', 0)
    unknown_conv = gender_total.get('미상', {}).get('conversions', 0)

    gender_summary = {
        'female_impr_pct': round(female_impr / total_impr * 100, 2) if total_impr else None,
        'male_impr_pct': round(male_impr / total_impr * 100, 4) if total_impr else None,
        'unknown_impr_pct': round(unknown_impr / total_impr * 100, 2) if total_impr else None,
        'unknown_conv_pct': round(unknown_conv / total_conv * 100, 2) if total_conv else None,
        'unknown_conv_count': unknown_conv,
        'unknown_impr_count': unknown_impr,
    }

    # 타겟팅 정합성 판정
    if male_impr == 0:
        gender_verdict = {
            'verdict': 'aligned',
            'label': '성별 타겟팅 의도대로 작동',
            'rationale': f'여성 노출 {gender_summary["female_impr_pct"]}% · 남성 노출 0건 — 남성 누수 없음. 미상 분류 {gender_summary["unknown_impr_pct"]}%',
        }
    elif male_impr / total_impr * 100 < 1:
        gender_verdict = {
            'verdict': 'minor_leak',
            'label': '경미한 남성 누수',
            'rationale': f'남성 노출 {gender_summary["male_impr_pct"]}% (1% 미만). 타겟팅은 의도대로 작동 중',
        }
    else:
        gender_verdict = {
            'verdict': 'leak',
            'label': '남성 노출 누수 감지',
            'rationale': f'남성 노출 {gender_summary["male_impr_pct"]}% — 타겟팅 설정 점검 필요',
        }

    # ---- 2. NONE(미상) 분류 이상 신호 ----
    none_anomaly = None
    if unknown_impr and total_impr:
        impr_share = unknown_impr / total_impr * 100
        conv_share = unknown_conv / total_conv * 100 if total_conv else 0
        # 노출 비중 대비 전환 비중이 5배 이상이면 어트리뷰션 비식별 정황
        if impr_share < 1 and conv_share > impr_share * 5 and unknown_conv >= 10:
            none_anomaly = {
                'verdict': 'attribution_unidentified',
                'label': '미상 분류 어트리뷰션 비식별 정황',
                'rationale': (
                    f'미상 노출 {impr_share:.2f}% / 미상 전환 {conv_share:.2f}% — 노출 대비 전환 비중 비대칭. '
                    f'cross-device 추정 또는 비식별 사용자의 전환 가능성. 운영 결정에는 직접 사용 금지'
                ),
                'unknown_impr_count': unknown_impr,
                'unknown_conv_count': unknown_conv,
                'impr_share': round(impr_share, 2),
                'conv_share': round(conv_share, 2),
            }

    # ---- 3. 연령 분포 (여성 한정) ----
    age_order = ['18-24', '25-34', '35-44', '45-54', '≥55', 'Unknown']
    by_age_female = {}
    fdf = df[df['gender'] == '여성']
    f_total_impr = int(fdf['impressions'].sum()) or 1
    for ag in age_order:
        sub = fdf[fdf['age_group'] == ag]
        if sub.empty:
            continue
        k = _kpis(sub)
        k['impr_share'] = round(k['impressions'] / f_total_impr * 100, 2)
        by_age_female[ag] = k

    # ---- 3-a. 25-34 운영 이력 (의도적 배제·재운영 추출) — age_signal 계산 전에 선행
    age_history = _extract_age_history(df, target_age='25-34', target_gender='여성')

    # 25-34 신호 해석 — 노출 비중 + CVR 효율을 함께 판단
    age_signal = None
    if '25-34' in by_age_female:
        target = by_age_female['25-34']
        target_cvr = target.get('cvr')
        target_share = target.get('impr_share')
        # 다른 연령대 CVR 평균 (25-34 제외, CVR 산정 가능한 그룹만)
        other_cvrs = [b['cvr'] for ag, b in by_age_female.items()
                      if ag != '25-34' and b.get('cvr') is not None and b['clicks'] >= 100]
        other_avg_cvr = round(sum(other_cvrs) / len(other_cvrs), 2) if other_cvrs else None

        if target_cvr is not None and other_avg_cvr is not None:
            cvr_ratio = round(target_cvr / other_avg_cvr, 2)
            if cvr_ratio < 0.5 and target_share < 15:
                age_signal = {
                    'verdict': 'inefficient',
                    'label': '25-34 확대 제외 — 별도 소재/랜딩 테스트 후 재판단',
                    'rationale': (
                        f'여성 25-34 노출 비중 {target_share}% (이미 낮음) · CVR {target_cvr}% — 다른 연령대 평균 CVR {other_avg_cvr}% 대비 '
                        f'{cvr_ratio*100:.0f}% 수준. 노출 비중이 작아 큰 개선 레버는 아니므로, 확대 대상에서 제외하고 '
                        '별도 소재·랜딩 메시지 테스트 후 다시 판단'
                    ),
                    'age_group': '25-34',
                    'impr_share': target_share,
                    'cvr': target_cvr,
                    'other_avg_cvr': other_avg_cvr,
                    'cvr_ratio': cvr_ratio,
                    'operation_context': age_history.get('context_note', ''),
                    'restart_branches': age_history.get('restart_branches', []),
                }
            elif cvr_ratio >= 1.0 and target_share < 15:
                age_signal = {
                    'verdict': 'undersupplied',
                    'label': '25-34 노출 부족 — 확대 기회',
                    'rationale': (
                        f'여성 25-34 노출 비중 {target_share}% · CVR {target_cvr}% (양호) — '
                        f'다른 연령대 평균 {other_avg_cvr}% 대비 {cvr_ratio*100:.0f}%. 입찰·예산 강화로 확대 검토'
                    ),
                    'age_group': '25-34',
                    'impr_share': target_share,
                    'cvr': target_cvr,
                    'other_avg_cvr': other_avg_cvr,
                    'cvr_ratio': cvr_ratio,
                }
            else:
                age_signal = {
                    'verdict': 'noop',
                    'label': '25-34 운영 균형 범위',
                    'rationale': f'노출 비중 {target_share}% · CVR {target_cvr}% (다른 연령대 평균 {other_avg_cvr}%) — 현 운영 유지',
                }
    # backward-compat
    age_undersupplied = age_signal if (age_signal and age_signal['verdict'] == 'undersupplied') else None

    # ---- 4. 지점별 성별 노출 정합성 ----
    by_branch = {}
    for b in VALID_BRANCHES + ['부산']:
        bdf = df[df['지점'] == b]
        if bdf.empty:
            continue
        bsum = {
            'total_impr': int(bdf['impressions'].sum()),
            'female_impr': int(bdf[bdf['gender'] == '여성']['impressions'].sum()),
            'male_impr': int(bdf[bdf['gender'] == '남성']['impressions'].sum()),
            'unknown_impr': int(bdf[bdf['gender'] == '미상']['impressions'].sum()),
            'female_conv': int(bdf[bdf['gender'] == '여성']['conversions'].sum()),
            'unknown_conv': int(bdf[bdf['gender'] == '미상']['conversions'].sum()),
            'total_conv': int(bdf['conversions'].sum()),
        }
        bsum['female_impr_pct'] = round(bsum['female_impr'] / bsum['total_impr'] * 100, 2) if bsum['total_impr'] else None
        bsum['unknown_conv_pct'] = round(bsum['unknown_conv'] / bsum['total_conv'] * 100, 2) if bsum['total_conv'] else None
        by_branch[b] = bsum

    # ---- 5. 권고 메시지 ----
    bullets = [gender_verdict['rationale']]
    if none_anomaly:
        bullets.append(none_anomaly['rationale'])
    if age_signal and age_signal['verdict'] != 'noop':
        bullets.append(age_signal['rationale'])

    # 운영 이력에서 한정 재운영 지점 정보 추출 (헤드라인·노트에 반영)
    restart_branches = age_history.get('restart_branches', []) if isinstance(age_history, dict) else []
    restart_suffix = (f' ({", ".join(restart_branches)} 한정 테스트 중)' if restart_branches else '')

    # 권고 헤드라인 — 신호 종류에 따라 분기
    if gender_verdict['verdict'] != 'aligned':
        headline = '타겟팅 정합성 점검 필요'
    elif age_signal and age_signal['verdict'] == 'inefficient':
        headline = f'성별 타겟팅 정상 — 25-34는 확대 제외 유지, {", ".join(restart_branches) if restart_branches else "한정 테스트"} 결과 추적' if restart_branches else '성별 타겟팅 정상 — 25-34는 확대 대상에서 제외, 별도 테스트로 검증'
    elif age_signal and age_signal['verdict'] == 'undersupplied':
        headline = '성별 타겟팅 정상 — 25-34 확대 기회 신호'
    else:
        headline = '타겟팅 정상 작동 — 누수 신호 없음'

    age_note = ''
    if age_signal and age_signal['verdict'] == 'inefficient':
        age_note = f'25-34 확대 제외 유지{restart_suffix}'
    elif age_signal and age_signal['verdict'] == 'undersupplied':
        age_note = '25-34 확대 기회'

    recommendation = {
        'headline': headline,
        'bullets': bullets,
        'tone': (
            '6월 운영은 지점·소재 단위 효율만이 아니라 성별·연령별 노출 품질까지 검증하여, '
            'CPA 변동의 원인을 소재 문제와 타겟 도달 문제로 분리합니다. 성별 타겟팅은 정상 작동 중이며, '
            f'주의 신호는 {", ".join([s for s in ["미상 분류 어트리뷰션" if none_anomaly else "", age_note] if s]) or "현재 없음"}입니다.'
        ),
    }

    return {
        'available': True,
        'data_period': f"{aud['date'].min().strftime('%Y-%m-%d')} ~ {aud['date'].max().strftime('%Y-%m-%d')}",
        'total': {
            'impressions': total_impr,
            'conversions': total_conv,
            'rows': int(len(aud)),
        },
        'gender_total': gender_total,
        'gender_summary': gender_summary,
        'gender_verdict': gender_verdict,
        'none_anomaly': none_anomaly,
        'by_age_female': by_age_female,
        'age_signal': age_signal,
        'age_undersupplied': age_undersupplied,
        'age_history': age_history,
        'by_branch': by_branch,
        'recommendation': recommendation,
        'note': (
            'TikTok 캠페인 성별 타겟팅 의도는 "여성 고정"이라는 운영 상수를 검증한 결과입니다. '
            '본 분석은 타겟팅 적용 정합성 진단용이며, 광고 그룹별 의사결정은 별도 모듈을 참조하세요.'
        ),
    }


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    aud = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260521/normalized_by_audience.parquet'
    parsed = sys.argv[2] if len(sys.argv) > 2 else 'output/data/20260521/parsed.parquet'
    r = analyze(aud, parsed)
    if not r.get('available'):
        print('[unavailable]', r.get('note'))
        sys.exit(0)
    print(f"[데이터 기간] {r['data_period']}")
    print(f"[총계] 노출 {r['total']['impressions']:,} · 전환 {r['total']['conversions']:,}")
    print()
    print(f"[성별] {r['gender_verdict']['label']}")
    print(f"  {r['gender_verdict']['rationale']}")
    print()
    if r['none_anomaly']:
        print(f"[NONE 이상] {r['none_anomaly']['label']}")
        print(f"  {r['none_anomaly']['rationale']}")
        print()
    print(f"[여성 연령 분포]")
    for ag, k in r['by_age_female'].items():
        print(f"  {ag}: 노출 {k['impressions']:,} ({k['impr_share']}%) · CVR {k['cvr']}% · CPA {k.get('cpa') or '-'}원")
    if r['age_signal']:
        print(f"  → {r['age_signal']['label']} — {r['age_signal']['rationale']}")
    print()
    print(f"[권고] {r['recommendation']['headline']}")
    print(r['recommendation']['tone'])
