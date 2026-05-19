"""6월 운영 제안서 HTML 빌더

5개 분석 결과를 통합하여 단일 HTML 리포트 생성.
산출: output/proposal/202606/proposal_daeat_202606.html
      output/proposal/202606/proposal_daeat_202606.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import VALID_BRANCHES, clean

sys.path.insert(0, str(Path(__file__).parent))
from analyze_funnel_by_month import analyze as analyze_funnel
from analyze_top_creatives import analyze as analyze_top
from build_june_targets import analyze as analyze_targets
from recommend_creatives import analyze as analyze_recommend
from analyze_addon_effect import analyze as analyze_addon
from analyze_root_cause import analyze as analyze_root
from build_action_table import analyze as analyze_action
from analyze_conversion_perspective import analyze as analyze_conv
from analyze_creative_type import analyze as analyze_ctype
from analyze_keyword import analyze as analyze_keyword
from analyze_lifecycle import analyze as analyze_lifecycle
from analyze_off_creatives import analyze as analyze_off
from analyze_cross_branch_variance import analyze as analyze_cross_var
from analyze_budget import analyze as analyze_budget
from analyze_funnel_variance import analyze as analyze_variance
from derive_consulting_signals import derive as derive_signals


def analyze_weekday_performance(parsed_path: str) -> dict:
    """요일별 성과 요약. 시간대 컬럼은 원천 데이터에 없어 요일만 분석한다."""
    df = pd.read_parquet(parsed_path).copy()
    df['date'] = pd.to_datetime(df['date'])
    # 정상 운영 월 중심. 5월 부분 데이터는 제외.
    df = df[df['date'].dt.month.isin([2, 3, 4])]
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    df['weekday_no'] = df['date'].dt.weekday
    df['weekday'] = df['weekday_no'].map(lambda i: weekdays[i])

    def agg(g):
        cost = int(g['cost'].sum())
        impressions = int(g['impressions'].sum())
        clicks = int(g['clicks'].sum())
        conversions = int(g['conversions'].sum())
        return {
            'cost': cost,
            'impressions': impressions,
            'clicks': clicks,
            'conversions': conversions,
            'cpm': round(cost / impressions * 1000) if impressions else None,
            'ctr': round(clicks / impressions * 100, 2) if impressions else None,
            'cvr': round(conversions / clicks * 100, 2) if clicks else None,
            'cpa': round(cost / conversions) if conversions else None,
        }

    overall = []
    for i, w in enumerate(weekdays):
        part = df[df['weekday_no'] == i]
        if part.empty:
            continue
        d = agg(part)
        d.update({'weekday': w, 'weekday_no': i})
        overall.append(d)

    by_branch = {}
    for branch, bdf in df.groupby('지점'):
        items = []
        for i, w in enumerate(weekdays):
            part = bdf[bdf['weekday_no'] == i]
            if part.empty:
                continue
            d = agg(part)
            d.update({'weekday': w, 'weekday_no': i})
            items.append(d)
        eligible = [x for x in items if x['conversions'] >= 10 and x['cpa']]
        if eligible:
            best = sorted(eligible, key=lambda x: (x['cpa'], -x['conversions']))[0]
            weak = sorted(eligible, key=lambda x: (x['cpa'], x['conversions']), reverse=True)[0]
        else:
            best = weak = None
        by_branch[branch] = {'items': items, 'best': best, 'weak': weak}

    eligible_overall = [x for x in overall if x['conversions'] >= 30 and x['cpa']]
    return {
        'note': '원천 데이터에 시간대 컬럼은 없어 요일별 성과만 분석. 시간대 운영은 TikTok Ads Manager 시간대 리포트 확인 후 적용 필요.',
        'overall': overall,
        'best_overall': sorted(eligible_overall, key=lambda x: (x['cpa'], -x['conversions']))[0] if eligible_overall else None,
        'weak_overall': sorted(eligible_overall, key=lambda x: (x['cpa'], x['conversions']), reverse=True)[0] if eligible_overall else None,
        'by_branch': by_branch,
    }


def build(parsed_path: str, meta_path: str, out_dir: str):
    print(f"[build] 분석 모듈 실행 중...")
    funnel = analyze_funnel(parsed_path)
    top = analyze_top(parsed_path)
    targets = analyze_targets(parsed_path)
    rec = analyze_recommend(parsed_path)
    addon = analyze_addon(parsed_path, meta_path)
    root_cause = analyze_root(parsed_path)
    action_table = analyze_action(parsed_path)
    conv_perspective = analyze_conv(parsed_path)
    creative_type = analyze_ctype(parsed_path)
    keyword_analysis = analyze_keyword(parsed_path)
    lifecycle = analyze_lifecycle(parsed_path)
    off_analysis = analyze_off(parsed_path)
    cross_variance = analyze_cross_var(parsed_path)
    weekday_performance = analyze_weekday_performance(parsed_path)
    budget = analyze_budget(parsed_path)
    funnel_variance = analyze_variance(parsed_path)

    # 컨설팅 보조 지표 (codex Round 2 권장)
    consulting_signals = derive_signals(
        june_targets=targets,
        root_cause=root_cause,
        conversion_perspective=conv_perspective,
        action_table=action_table,
        recommendations=rec,
        top_creatives=top,
        creative_type=creative_type,
        keyword_analysis=keyword_analysis,
    )

    payload = {
        'meta': {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'data_period': f"{funnel['months'][0]} ~ {funnel['months'][-1]} (마지막: {funnel['last_date']})",
            'branches': VALID_BRANCHES,
            'campaign_objective': '전환 수 증대 (주요 목적)',
            'partial_month_note': '2026-05는 운영 도중 중단된 부분 데이터 (15일까지). 월 환산 무의미하므로 6월 계획 베이스라인은 4월을 사용.',
        },
        'funnel_by_month': funnel,
        'top_creatives': top,
        'june_targets': targets,
        'recommendations': rec,
        'addon_effect': addon,
        'root_cause': root_cause,
        'action_table': action_table,
        'conversion_perspective': conv_perspective,
        'creative_type': creative_type,
        'keyword_analysis': keyword_analysis,
        'lifecycle': lifecycle,
        'off_analysis': off_analysis,
        'cross_variance': cross_variance,
        'weekday_performance': weekday_performance,
        'budget': budget,
        'funnel_variance': funnel_variance,
        'consulting_signals': consulting_signals,
    }
    payload = clean(payload)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / 'proposal_daeat_202606.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[save] {json_path}")

    html = render_html(payload)
    html_path = out / 'proposal_daeat_202606.html'
    html_path.write_text(html, encoding='utf-8')
    print(f"[save] {html_path}")


def render_html(data: dict) -> str:
    """컨설팅 보고서 v2 — html_template.py + js_body.py 사용."""
    from html_template import HTML_TEMPLATE as TEMPLATE_V2
    from js_body import JS_BODY
    data_json = json.dumps(data, ensure_ascii=False)
    return TEMPLATE_V2.replace('__JS_BODY__', JS_BODY).replace('__DATA_JSON__', data_json)


if __name__ == '__main__':
    parsed = sys.argv[1] if len(sys.argv) > 1 else 'output/data/20260506/parsed.parquet'
    meta = sys.argv[2] if len(sys.argv) > 2 else 'input/tiktok_ad_meta.csv'
    out = sys.argv[3] if len(sys.argv) > 3 else 'output/proposal/202606'
    build(parsed, meta, out)
