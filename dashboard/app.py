"""6월 TikTok 운영 콘솔 — Flask 부트 + 라우트

실행:
  python -m dashboard.app
  → http://localhost:5050
"""
from __future__ import annotations

import json
import sys
from collections import OrderedDict, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, abort

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / '.claude' / 'skills'))

from dashboard.services.data_loader import load_bundle, invalidate_cache, save_checklist_state
from dashboard.services.kpi_progress import compute as compute_kpi, summary_status
from dashboard.services.alert_engine import detect_alerts
from dashboard.services.checklist_engine import evaluate as evaluate_checklist, summary as checklist_summary
from dashboard.services.action_recommender import generate as generate_actions, total_action_count
from dashboard.services.action_tracker import log_action, list_actions
from dashboard.services.branch_detail import build as build_branch
from dashboard.services.creative_detail import build as build_creative


app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / 'templates'),
    static_folder=str(Path(__file__).parent / 'static'),
)


def _today_for_context() -> date:
    override = request.args.get('today') if request else None
    if override:
        try:
            return datetime.strptime(override, '%Y-%m-%d').date()
        except ValueError:
            pass
    return date.today()


def _common_ctx() -> dict:
    bundle = load_bundle()
    today = _today_for_context()
    return {
        'today': today.strftime('%Y-%m-%d'),
        'today_param': request.args.get('today') or '',
        'data_dir': bundle.data_dir.name,
        '_bundle': bundle,
        '_today': today,
    }


@app.route('/')
def home():
    ctx = _common_ctx()
    bundle, today = ctx.pop('_bundle'), ctx.pop('_today')
    kpi = compute_kpi(bundle, today=today)
    alerts = detect_alerts(bundle, today=today)
    checklist = evaluate_checklist(bundle)
    recs = generate_actions(bundle)
    return render_template(
        'home.html', active='home',
        **ctx,
        kpi=kpi, kpi_status=summary_status(kpi),
        alerts=alerts, alert_count=len([a for a in alerts if not a.suppressed]),
        checklist=checklist, checklist_stats=checklist_summary(checklist),
        recs=recs, action_count=total_action_count(recs),
        recent_actions=list_actions(bundle, limit=10),
    )


@app.route('/branch/<branch_name>')
def branch_detail(branch_name: str):
    ctx = _common_ctx()
    bundle, today = ctx.pop('_bundle'), ctx.pop('_today')
    try:
        common_mod = __import__('common', fromlist=['VALID_BRANCHES'])
        valid = set(common_mod.VALID_BRANCHES)
    except Exception:
        valid = set()
    if valid and branch_name not in valid:
        abort(404)
    detail = build_branch(bundle, branch_name, today=today)
    return render_template('branch.html', active='home', detail=detail, **ctx)


@app.route('/creative/<creative_name>')
def creative_detail(creative_name: str):
    ctx = _common_ctx()
    bundle, today = ctx.pop('_bundle'), ctx.pop('_today')
    detail = build_creative(bundle, creative_name, today=today)
    return render_template('creative.html', active='home', detail=detail, **ctx)


@app.route('/checklist')
def checklist_page():
    ctx = _common_ctx()
    bundle = ctx.pop('_bundle'); ctx.pop('_today')
    items = evaluate_checklist(bundle)
    # 주차별 그룹 + 정렬
    grouped = OrderedDict()
    for week_label in ['W1', 'W2-W3', 'W4', '기타']:
        grouped[week_label] = []
    for it in items:
        key = it.week if it.week in grouped else '기타'
        grouped[key].append(it)
    grouped = OrderedDict((k, v) for k, v in grouped.items() if v)
    return render_template(
        'checklist.html', active='checklist',
        **ctx,
        grouped_by_week=grouped, stats=checklist_summary(items),
    )


@app.route('/tracker')
def tracker_page():
    ctx = _common_ctx()
    bundle = ctx.pop('_bundle'); ctx.pop('_today')
    # 필터
    filters = {
        'action_type': request.args.get('action_type', ''),
        'branch': request.args.get('branch', ''),
        'from_date': request.args.get('from_date', ''),
        'to_date': request.args.get('to_date', ''),
    }
    actions = list_actions(bundle, limit=1000)
    if filters['action_type']:
        actions = [a for a in actions if a.get('action_type') == filters['action_type']]
    if filters['branch']:
        actions = [a for a in actions if a.get('branch') == filters['branch']]
    if filters['from_date']:
        actions = [a for a in actions if a.get('date', '') >= filters['from_date']]
    if filters['to_date']:
        actions = [a for a in actions if a.get('date', '') <= filters['to_date']]
    # 통계
    all_actions = list_actions(bundle, limit=10000)
    stats = {
        'total': len(all_actions),
        'd1_done': sum(1 for a in all_actions if (a.get('effects') or {}).get('d1')),
        'd3_done': sum(1 for a in all_actions if (a.get('effects') or {}).get('d3')),
        'd7_done': sum(1 for a in all_actions if (a.get('effects') or {}).get('d7')),
        'pending': sum(1 for a in all_actions if not all((a.get('effects') or {}).get(k) for k in ['d1','d3','d7'])),
    }
    # 필터 옵션
    common_mod = __import__('common', fromlist=['VALID_BRANCHES'])
    filter_options = {
        'action_types': sorted({a.get('action_type', '') for a in all_actions if a.get('action_type')}),
        'branches': common_mod.VALID_BRANCHES,
    }
    # 평균 효과 (action_type별 D+7)
    avg_effects = _compute_avg_effects(all_actions)
    return render_template(
        'tracker.html', active='tracker',
        **ctx,
        actions=actions, stats=stats, filters=filters,
        filter_options=filter_options, avg_effects=avg_effects,
    )


def _compute_avg_effects(actions: list) -> list:
    """action_type별 D+7 평균 효과 (before·after KPI 추출 가능한 경우만)."""
    by_type = defaultdict(list)
    for a in actions:
        d7 = (a.get('effects') or {}).get('d7')
        if not d7:
            continue
        # before·after에서 CPA·CVR 추출 시도 (단순 케이스만)
        # MVP — D+7 KPI만 사용해서 액션 type별 평균 산출
        if d7.get('cpa') is not None and d7.get('cvr') is not None:
            by_type[a.get('action_type', 'unknown')].append({
                'cpa': d7.get('cpa'), 'cvr': d7.get('cvr')
            })
    out = []
    for at, items in by_type.items():
        if not items:
            continue
        # MVP: 평균 CPA·CVR만 — 추세 비교는 Phase 3로
        avg_cpa = sum(i['cpa'] for i in items) / len(items)
        avg_cvr = sum(i['cvr'] for i in items) / len(items)
        out.append({
            'action_type': at,
            'count': len(items),
            'cpa_delta_pct': None,   # MVP에서는 비교 baseline 없음 — 향후 before/after 비교 추가
            'cvr_delta_pct': None,
        })
    return out


@app.route('/refresh', methods=['POST'])
def refresh():
    invalidate_cache()
    return redirect(request.referrer or url_for('home'))


@app.route('/tracker/log', methods=['POST'])
def tracker_log():
    payload = request.json or request.form.to_dict()
    action = log_action(
        action_type=payload.get('action_type', 'unknown'),
        reason=payload.get('reason', ''),
        branch=payload.get('branch'),
        ad_id=payload.get('ad_id'),
        creative_name=payload.get('creative_name'),
        before=payload.get('before'),
        after=payload.get('after'),
        expected_metric=payload.get('expected_metric'),
        operator=payload.get('operator', 'agency'),
        linked_alert_id=payload.get('linked_alert_id'),
        linked_checklist_id=payload.get('linked_checklist_id'),
    )
    return jsonify(action)


@app.route('/checklist/toggle', methods=['POST'])
def checklist_toggle():
    cid = request.json.get('id') if request.is_json else request.form.get('id')
    checked = request.json.get('checked') if request.is_json else request.form.get('checked') == 'true'
    note = (request.json or {}).get('note') or request.form.get('note', '')
    bundle = load_bundle()
    state = dict(bundle.checklist_state or {})
    state[cid] = {
        'checked': bool(checked),
        'checked_at': datetime.now().isoformat(timespec='seconds'),
        'note': note,
    }
    save_checklist_state(state)
    return jsonify({'ok': True, 'id': cid, 'checked': bool(checked)})


# Jinja2 필터
@app.template_filter('won')
def filter_won(value):
    if value is None or value == '' or (isinstance(value, float) and value != value):
        return '-'
    try:
        return f'{int(value):,}원'
    except (ValueError, TypeError):
        return '-'


@app.template_filter('count')
def filter_count(value):
    if value is None or (isinstance(value, float) and value != value):
        return '-'
    try:
        return f'{int(value):,}'
    except (ValueError, TypeError):
        return '-'


@app.template_filter('pct')
def filter_pct(value, decimals=1):
    if value is None or (isinstance(value, float) and value != value):
        return '-'
    try:
        return f'{float(value):.{decimals}f}%'
    except (ValueError, TypeError):
        return '-'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
