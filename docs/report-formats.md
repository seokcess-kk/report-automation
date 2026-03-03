# 3종 리포트 시스템

| 리포트 | 파일 | 발행 주기 | 수신자 |
|--------|------|----------|--------|
| 데일리 | `tiktok_daily_YYYYMMDD.md` | 매일 아침 | 내부 (쏭) |
| 위클리 | `tiktok_weekly_dayt_YYYYMMDD.html` | 매주 월요일 | 클라이언트 |
| 먼슬리 | `tiktok_monthly_dayt_YYYYMM.html` | 익월 1~3일 | 클라이언트 + 의사결정자 |

---

## 데일리 리포트 (Markdown)

```markdown
📊 [MM/DD] 다이트한의원 TikTok 전일 성과

📌 전체
• 전환: XX건 (전일 대비 ±XX건)
• CPA: XX,XXX원 (전일 대비 ±X,XXX원)
• CTR: X.XX% (전일 대비 ±X.XX%p)

🏢 지점별
• 서울: CPA XX,XXX원 (±XX원) | CTR X.XX% (±X.XXp)
[... 각 지점 1줄]

⚠️ 이상 감지
• [지점] [소재명] — CPA X.Xx배 (지점 평균 대비), OFF 검토 권고
• (없으면 "이상 없음")
```

**이상 감지 기준**: CPA가 지점 평균의 2배 이상 AND 비용 ≥ 지점평균CPA × 2

### 데일리 스냅샷 관리

```
경로: output/daily/daily_snapshot.json
구조: {"YYYY-MM-DD": {"total": {...}, "branch": {...}}}
```

- 매일 실행 후 **전일 데이터를 스냅샷에 저장**
- 전일 대비 계산 = 오늘 데이터 - `snapshot[어제 날짜]`
- 스냅샷 없으면 전일 대비 항목은 **"N/A"** 표시
- 스냅샷은 최근 30일분만 유지 (오래된 것 자동 삭제)

---

## 위클리 리포트 (HTML 단일 스크롤)

> **⚠️ TIER 기준 (위클리 전용)**
> - 해당 주 7일 데이터만 사용 (월간 누적 아님)
> - **LOW_VOLUME**: 클릭 < 50 AND 비용 < 50,000원
> - **UNCLASSIFIED**: 집행일수 < 3일

**섹션 구성**:
1. 헤더 — 분석기간, 비교기간, 발행일
2. 이번 주 KPI — 전주 대비 (광고비, 전환, CPA, CTR, CVR)
3. 핵심 인사이트 — 변화 원인 분석
4. 소재 TIER 현황 — 이번 주 TIER + 전주 대비 변동
5. 지점별 성과 — CPA/CTR/CVR 전주 대비 차트 + 테이블
6. 예산 페이스 — 지점별 소진율 vs 기간 경과율
7. 소재 ON/OFF 액션플랜 — OFF 권고 / ON 권고
8. 이번 달 전환 목표 달성 예상

---

## 먼슬리 리포트 (HTML 7탭)

**7탭 구조**:
1. **월간 요약** — KPI 카드 6개, TIER 분포 도넛, 지점별 CPA 바차트
2. **소재 TIER** — 버블차트, ON 소재 테이블, **OFF 소재 성과**, **OFF 전후 CPA 참고**
3. **지점 분석** — CPA/효율 차트, 소재×지점 CPA 편차, 지점×나이대 히트맵
4. **나이대 분석** — 비용비중 vs 전환비중, 소재유형×나이대 히트맵
5. **소재 수명** — 신규 vs 재가공 비교, 집행일수별 CTR 추이
6. **일별 트렌드** — 광고비+전환수 콤보차트, CTR/CPA 추이
7. **다음 달 전략** — 예산 배분 권고, 신규 소재 기획 방향

---

## OFF 소재 처리 원칙

### 판별 방식

```python
df['is_off'] = df['ad_name'].str.lower().str.endswith('_off')
df_on  = df[~df['is_off']]   # KPI·TIER 계산에 사용
df_off = df[df['is_off']]    # OFF 분석 섹션에만 사용
```

### 원칙

- OFF 소재는 **KPI/TIER 계산 전체에서 제외**
- OFF 소재명: `_off` 접미사만 제거, 나머지 원본 유지
- OFF 소재는 별도 `off_perf` + `before_after` 섹션에만 표시

### before_after 분석 스키마

OFF 소재별 OFF 전후 지점 CPA 참고 분석.
**⚠️ 인과관계 아님** — 지점 전체 CPA이며 복합 요인 반영.

```json
{
  "creative_name": "광고명 원본(_off 제외)",
  "branch": "지점명",
  "off_date": "MM/DD",
  "before_cpa": int, "before_days": int,
  "after_cpa": int,  "after_days": int,
  "cpa_change_pct": float,
  "share_pct": float,
  "impact_level": "high|mid|low",
  "reliability": "high|mid|low|no_after"
}
```

**점유율 기준**: ≥20% → high, ≥8% → mid, <8% → low

**신뢰도 기준**:
- `after_days == 0` → `no_after`
- `after_days ≤ 2` → `low`
- `after_days ≤ 5` → `mid`
- `after_days > 5` → `high`

---

## 먼슬리 리포트 상세 기준 (v3.4)

### 예산 배분 권고 (다음 달 전략 탭)

**효율점수 공식**: `전환비중 / 비용비중`

| 효율점수 | 색상 | 권고 | 예산 조정 |
|----------|------|------|-----------|
| ≥ 1.2 | 녹색 (#4ade80) | 증액 권고 | ×1.15 |
| 0.8 ~ 1.2 | 파랑 (#60a5fa) | 유지 | 현행 유지 |
| < 0.8 | 빨강 (#f87171) | 감액 검토 | ×0.85 |

### 신규 vs 재가공 비교 (소재 수명 탭)

**차트 구성**:
- 막대 차트: CPA 비교 (신규 / 재가공)
- 선 그래프: CTR/CVR 비교

**상세 테이블 컬럼**:
| 구분 | 소재수 | 비용 | 전환 | CPA | CTR | CVR |
|------|--------|------|------|-----|-----|-----|

### 신규 소재 섹션 (소재 TIER 탭)

- **대상**: 집행일수 < 7일 (UNCLASSIFIED)
- **표시 컬럼**: 소재명, 지점, 비용, 전환, CPA, CTR, CVR
- **용도**: 초기 성과 모니터링, 향후 TIER 분류 대상

### Before/After 필터 (OFF 전후 탭)

- **소재명 드롭다운**: OFF된 소재 선택
- **지점 드롭다운**: 지점별 필터링
- 양쪽 모두 **"전체"** 옵션 포함
- 필터 연동: 소재+지점 복합 필터링 지원
