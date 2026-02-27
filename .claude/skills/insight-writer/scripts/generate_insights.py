"""
AI 인사이트 생성
설계서 섹션 9 기준

인사이트 작성 원칙:
- 형식: 수치 근거 → 해석 → 액션 제안
- 등급: 확정 인사이트 (표본 충분) / 가설 인사이트 (표본 부족)

금지 표현:
- 단일 나이대 소량 데이터로 단정하는 표현
- 클릭0/전환>0 행 기반 단정 표현
- "최고 효율" 등 단정 표현 (LOW_VOLUME 소재에)
"""
import pandas as pd
import numpy as np
import os
from datetime import datetime


class InsightGenerator:
    """인사이트 생성기"""

    def __init__(self, creative_df, age_df, hook_df, anomaly_df, funnel_insights=None):
        self.creative_df = creative_df
        self.age_df = age_df
        self.hook_df = hook_df
        self.anomaly_df = anomaly_df
        self.funnel_insights = funnel_insights or []
        self.insights = []

    def add_insight(self, category: str, level: str, title: str, content: str, action: str,
                    confidence: str = '확정', metrics: dict = None):
        """인사이트 추가"""
        self.insights.append({
            'category': category,
            'level': level,  # 'high', 'medium', 'low'
            'title': title,
            'content': content,
            'action': action,
            'confidence': confidence,  # '확정' or '가설'
            'metrics': metrics or {}
        })

    def generate_tier_insights(self):
        """TIER 기반 인사이트 생성"""
        if self.creative_df is None or len(self.creative_df) == 0:
            return

        # TIER1 소재 분석
        tier1 = self.creative_df[self.creative_df['TIER'] == 'TIER1']
        if len(tier1) > 0:
            best = tier1.nsmallest(1, 'CPA').iloc[0]
            self.add_insight(
                category='CREATIVE',
                level='high',
                title='최고 성과 소재 발견',
                content=f"'{best['소재명']}' 소재가 CPA {best['CPA']:,.0f}원, CVR {best['CVR']:.1f}%로 "
                        f"전 지표 최우수 성과를 기록했습니다.",
                action=f"현재 {', '.join(best['집행지점목록']) if isinstance(best['집행지점목록'], list) else best['집행지점목록']} "
                       f"지점에서 집행 중이며, 미집행 지점으로 확대를 권장합니다.",
                confidence='확정',
                metrics={'CPA': best['CPA'], 'CVR': best['CVR'], 'CTR': best['CTR']}
            )

        # TIER4 소재 분석
        tier4 = self.creative_df[self.creative_df['TIER'] == 'TIER4']
        if len(tier4) >= 3:
            self.add_insight(
                category='CREATIVE',
                level='medium',
                title='성과 미달 소재',
                content=f"TIER4(성과 미달) 소재가 {len(tier4)}개 존재합니다. "
                        f"CTR, CPA, 랜딩률 모두 평균 이하입니다.",
                action="해당 소재의 썸네일/훅 변경 또는 예산 재배분을 검토하세요.",
                confidence='확정'
            )

        # LOW_VOLUME 소재 주의
        low_vol = self.creative_df[self.creative_df['TIER'] == 'LOW_VOLUME']
        if len(low_vol) > 0:
            self.add_insight(
                category='DATA_QUALITY',
                level='low',
                title='데이터 부족 주의',
                content=f"{len(low_vol)}개 소재가 표본 부족(클릭 <100 AND 비용 <10만원)으로 "
                        f"정확한 성과 평가가 어렵습니다.",
                action="추가 예산 집행 후 재평가하거나, 집행 중단을 검토하세요.",
                confidence='가설'
            )

    def generate_age_insights(self):
        """나이대 기반 인사이트 생성"""
        if self.age_df is None or len(self.age_df) == 0:
            return

        # 효율 우수 나이대
        efficient = self.age_df[self.age_df['예산효율점수'] >= 1.2]
        if len(efficient) > 0:
            for _, row in efficient.iterrows():
                self.add_insight(
                    category='TARGETING',
                    level='high',
                    title=f'{row["age_group"]} 나이대 고효율',
                    content=f"{row['age_group']} 나이대가 비용 대비 전환 효율이 높습니다. "
                            f"(비용 {row['비용비중']:.1f}% → 전환 {row['전환비중']:.1f}%)",
                    action="해당 나이대 타겟팅 비중 확대를 검토하세요.",
                    confidence='확정',
                    metrics={'효율점수': row['예산효율점수'], 'CPA': row['CPA']}
                )

        # 비효율 나이대
        inefficient = self.age_df[self.age_df['예산효율점수'] < 0.5]
        if len(inefficient) > 0:
            for _, row in inefficient.iterrows():
                caution = row.get('귀속주의', 0)
                confidence = '가설' if caution > 5 else '확정'

                self.add_insight(
                    category='TARGETING',
                    level='medium',
                    title=f'{row["age_group"]} 나이대 저효율',
                    content=f"{row['age_group']} 나이대가 비용 대비 전환 효율이 낮습니다. "
                            f"(비용 {row['비용비중']:.1f}% → 전환 {row['전환비중']:.1f}%)",
                    action="해당 나이대 맞춤 소재 개발 또는 타겟팅 축소를 검토하세요.",
                    confidence=confidence,
                    metrics={'효율점수': row['예산효율점수'], 'CPA': row['CPA']}
                )

    def generate_hook_insights(self):
        """훅 비교 기반 인사이트 생성"""
        if self.hook_df is None or len(self.hook_df) == 0:
            return

        for _, row in self.hook_df.iterrows():
            verdict = row.get('훅판정', '')
            ctr_change = row.get('CTR_변화율', 0)

            if '재가공 유효' in verdict:
                # CTR+, CVR+ → 재가공 유효
                self.add_insight(
                    category='CREATIVE_OPTIMIZATION',
                    level='high',
                    title=f'{row["소재유형"]} 재가공 훅 효과 있음',
                    content=f"{row['소재유형']} 유형에서 재가공 훅이 효과적입니다. "
                            f"CTR {ctr_change:+.1f}%, CVR도 개선되었습니다.",
                    action="재가공 전략을 다른 소재에도 적용하세요.",
                    confidence='확정'
                )
            elif '부분 효과' in verdict:
                # CTR+ but CVR- 또는 CTR- but CVR+ → 부분 효과
                self.add_insight(
                    category='CREATIVE_OPTIMIZATION',
                    level='medium',
                    title=f'{row["소재유형"]} 훅 부분 효과',
                    content=f"{row['소재유형']} 유형에서 재가공 훅이 부분적으로 효과가 있습니다. "
                            f"CTR {ctr_change:+.1f}% 변화. 랜딩 페이지 점검이 필요합니다.",
                    action="랜딩 페이지와 훅 메시지 일치 여부를 확인하세요.",
                    confidence='확정'
                )
            elif '효과 없음' in verdict:
                # CTR-, CVR- → 재가공 효과 없음
                self.add_insight(
                    category='CREATIVE_OPTIMIZATION',
                    level='medium',
                    title=f'{row["소재유형"]} 훅 효과 없음',
                    content=f"{row['소재유형']} 유형에서 재가공 훅이 효과가 없습니다. "
                            f"CTR {ctr_change:+.1f}% 변화.",
                    action="원본 훅으로 복귀하거나 새로운 훅 전략을 테스트하세요.",
                    confidence='확정'
                )

    def generate_anomaly_insights(self):
        """이상치 기반 인사이트 생성"""
        if self.anomaly_df is None or len(self.anomaly_df) == 0:
            return

        # 귀속 주의
        attribution = self.anomaly_df[self.anomaly_df['감지유형'] == 'attribution']
        if len(attribution) > 10:
            self.add_insight(
                category='DATA_QUALITY',
                level='medium',
                title='귀속 주의',
                content=f"클릭=0이지만 전환>0인 데이터가 {len(attribution)}건 있습니다. "
                        f"뷰스루 전환 또는 지연 전환으로 추정됩니다.",
                action="CVR 해석 시 주의가 필요하며, 전환 경로 분석을 권장합니다.",
                confidence='가설'
            )

        # 지점별 편차
        branch_var = self.anomaly_df[self.anomaly_df['감지유형'] == 'branch_variance']
        if len(branch_var) > 0:
            for _, row in branch_var.iterrows():
                if pd.notna(row.get('소재명')):
                    self.add_insight(
                        category='BRANCH',
                        level='medium',
                        title=f"'{row['소재명']}' 지점별 편차",
                        content=f"동일 소재인데 지점간 CPA 차이가 {row.get('CPA_배율', 0):.1f}배입니다. "
                                f"({row.get('최저CPA_지점', 'N/A')} {row.get('최저CPA', 0):,.0f}원 vs "
                                f"{row.get('최고CPA_지점', 'N/A')} {row.get('최고CPA', 0):,.0f}원)",
                        action=row.get('권장조치', '지점별 요인 분석 필요'),
                        confidence='확정'
                    )

    def generate_funnel_insights_from_data(self):
        """퍼널 인사이트 추가"""
        for insight in self.funnel_insights:
            self.add_insight(
                category='FUNNEL',
                level='medium',
                title=insight.get('type', '퍼널 인사이트'),
                content=insight.get('insight', ''),
                action='퍼널 개선 검토',
                confidence='확정' if 'WARNING' not in insight.get('type', '') else '가설'
            )

    def generate_action_plan(self) -> list:
        """액션 플랜 생성"""
        actions = []

        # 우선순위별 정렬
        high_insights = [i for i in self.insights if i['level'] == 'high']
        medium_insights = [i for i in self.insights if i['level'] == 'medium']

        # 이번 주 추천 액션
        actions.append({
            'priority': 1,
            'action': 'TIER1 소재 확대',
            'description': f"TIER1 소재 {len(self.creative_df[self.creative_df['TIER']=='TIER1']) if self.creative_df is not None else 0}개의 "
                          f"예산 비중을 늘리고 미집행 지점으로 확장하세요."
        })

        if len(high_insights) > 0:
            actions.append({
                'priority': 2,
                'action': high_insights[0]['title'],
                'description': high_insights[0]['action']
            })

        if len(medium_insights) > 0:
            actions.append({
                'priority': 3,
                'action': 'TIER4 소재 개선',
                'description': "성과 미달 소재의 훅/썸네일 변경 또는 예산 재배분을 진행하세요."
            })

        return actions

    def generate_all(self) -> dict:
        """모든 인사이트 생성"""
        self.generate_tier_insights()
        self.generate_age_insights()
        self.generate_hook_insights()
        self.generate_anomaly_insights()
        self.generate_funnel_insights_from_data()

        action_plan = self.generate_action_plan()

        return {
            'insights': self.insights,
            'action_plan': action_plan,
            'summary': {
                'total_insights': len(self.insights),
                'high_priority': len([i for i in self.insights if i['level'] == 'high']),
                'confirmed': len([i for i in self.insights if i['confidence'] == '확정']),
                'hypothesis': len([i for i in self.insights if i['confidence'] == '가설']),
            }
        }


def generate_improvement_suggestions(insights_result: dict, output_dir: str) -> str:
    """
    improvement_suggestions.md 자동 생성
    """
    md_content = f"""# TikTok 광고 분석 - 개선 제안

생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 요약
- 총 인사이트: {insights_result['summary']['total_insights']}건
- 높은 우선순위: {insights_result['summary']['high_priority']}건
- 확정 인사이트: {insights_result['summary']['confirmed']}건
- 가설 인사이트: {insights_result['summary']['hypothesis']}건

---

## 이번 주 액션 플랜

"""
    for action in insights_result['action_plan']:
        md_content += f"### 우선순위 {action['priority']}: {action['action']}\n"
        md_content += f"{action['description']}\n\n"

    md_content += """---

## 상세 인사이트

"""
    # 카테고리별 그룹핑
    categories = {}
    for insight in insights_result['insights']:
        cat = insight['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(insight)

    # 카테고리명 한글 매핑
    cat_name_map = {
        'CREATIVE': '소재 성과',
        'TARGETING': '타겟팅',
        'CREATIVE_OPTIMIZATION': '소재 최적화',
        'DATA_QUALITY': '데이터 품질',
        'BRANCH': '지점 분석',
        'FUNNEL': '퍼널 분석',
    }

    for cat, cat_insights in categories.items():
        cat_display = cat_name_map.get(cat, cat)
        md_content += f"### {cat_display}\n\n"
        for insight in cat_insights:
            level_emoji = {'high': '[!]', 'medium': '[*]', 'low': '[-]'}
            md_content += f"**{level_emoji.get(insight['level'], '')} {insight['title']}** "
            md_content += f"({insight['confidence']})\n\n"
            md_content += f"{insight['content']}\n\n"
            md_content += f"> 액션: {insight['action']}\n\n"

    md_content += """---

## 데이터 품질 참고사항

- '가설' 표시된 인사이트는 추가 데이터로 검증이 필요합니다.
- 귀속 주의 행 (클릭=0, 전환>0)이 CVR 계산에 영향을 줄 수 있습니다.
- LOW_VOLUME 소재는 더 많은 데이터가 필요합니다.

---

*이 문서는 자동 생성되었습니다. 직접 수정하지 마세요.*
"""

    # 저장
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "improvement_suggestions.md")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"[OK] Improvement suggestions -> {output_path}")

    return output_path


def main(data_dir: str = "output", output_dir: str = None):
    """메인 실행"""
    if output_dir is None:
        today = datetime.now().strftime('%Y%m%d')
        output_dir = os.path.join(data_dir, today)

    # 데이터 로드
    try:
        creative_df = pd.read_parquet(os.path.join(data_dir, "creative_tier.parquet"))
    except FileNotFoundError:
        creative_df = None

    try:
        age_df = pd.read_parquet(os.path.join(data_dir, "age_analysis.parquet"))
    except FileNotFoundError:
        age_df = None

    try:
        hook_df = pd.read_parquet(os.path.join(data_dir, "hook_type_comparison.parquet"))
    except FileNotFoundError:
        hook_df = None

    try:
        anomaly_df = pd.read_csv(os.path.join(data_dir, "anomalies.csv"))
    except FileNotFoundError:
        anomaly_df = None

    # 인사이트 생성
    generator = InsightGenerator(creative_df, age_df, hook_df, anomaly_df)
    result = generator.generate_all()

    print(f"\n[Insight Generation]")
    print(f"  - Total: {result['summary']['total_insights']}")
    print(f"  - High Priority: {result['summary']['high_priority']}")
    print(f"  - Confirmed: {result['summary']['confirmed']}")

    # improvement_suggestions.md 생성
    generate_improvement_suggestions(result, output_dir)

    return result


if __name__ == "__main__":
    import sys
    data_directory = sys.argv[1] if len(sys.argv) > 1 else "output"
    output_directory = sys.argv[2] if len(sys.argv) > 2 else None
    main(data_directory, output_directory)
