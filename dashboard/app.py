"""6월 TikTok 운영 콘솔 — Flask 부트 + 라우트

실행:
  python -m dashboard.app
  → http://localhost:5050
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / '.claude' / 'skills'))

from dashboard.services.data_loader import load_bundle, invalidate_cache, save_checklist_state
from dashboard.services.kpi_progress import compute as compute_kpi, summary_status
from dashboard.services.alert_engine import detect_alerts
from dashboard.services.checklist_engine import evaluate as evaluate_checklist, summary as checklist_summary
from dashboard.services.action_recommender import generate as generate_actions, total_action_count
from dashboard.services.action_tracker import log_action, list_actions


app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / 'templates'),
    static_folder=str(Path(__file__).parent / 'static'),
)


def _today_for_context() -> date:
    """오버라이드 가능 — 5월 부분월 시연용. 실제 운영 시 date.today()."""
    override = request.args.get('today') if request else None
    if override:
        try:
            return datetime.strptime(override, '%Y-%m-%d').date()
        except ValueError:
            pass
    return date.today()


@app.route('/')
def home():
    today = _today_for_context()
    bundle = load_bundle()
    kpi = compute_kpi(bundle, today=today)
    alerts = detect_alerts(bundle, today=today)
    checklist = evaluate_checklist(bundle)
    recs = generate_actions(bundle)
    return render_template(
        'home.html',
        today=today.strftime('%Y-%m-%d'),
        data_dir=bundle.data_dir.name,
        kpi=kpi,
        kpi_status=summary_status(kpi),
        alerts=alerts,
        alert_count=len([a for a in alerts if not a.suppressed]),
        checklist=checklist,
        checklist_stats=checklist_summary(checklist),
        recs=recs,
        action_count=total_action_count(recs),
        recent_actions=list_actions(bundle, limit=10),
    )


@app.route('/refresh', methods=['POST'])
def refresh():
    invalidate_cache()
    return redirect(url_for('home'))


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
    if value is None or value == '' or value != value:   # NaN
        return '-'
    try:
        return f'{int(value):,}원'
    except (ValueError, TypeError):
        return '-'


@app.template_filter('count')
def filter_count(value):
    if value is None:
        return '-'
    try:
        return f'{int(value):,}'
    except (ValueError, TypeError):
        return '-'


@app.template_filter('pct')
def filter_pct(value, decimals=1):
    if value is None or value != value:
        return '-'
    try:
        return f'{float(value):.{decimals}f}%'
    except (ValueError, TypeError):
        return '-'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
