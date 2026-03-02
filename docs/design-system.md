# 디자인 시스템

## 디자인 레퍼런스

HTML 리포트 생성 시 **반드시 아래 파일을 먼저 읽고** 디자인 시스템 통일:

```
레퍼런스: output/_ref/monthly_ref.html ← 확정된 디자인 기준 (먼슬리)
레퍼런스: output/_ref/weekly_ref.html  ← 확정된 디자인 기준 (위클리)
```

- 위클리/데일리는 이 파일과 **같은 시리즈처럼 보여야 함**
- CSS 변수, 폰트, 차트 설정을 **그대로 따를 것**
- 새 리포트 빌더 작성 시 먼슬리 HTML 구조를 참고

---

## CSS 변수

```css
:root {
  --bg: #0b0d12;
  --s1: #11141c;
  --s2: #171b25;
  --bd: #1c2030;
  --acc: #4ade80;    /* 성공/좋음/TIER1 */
  --blue: #60a5fa;   /* 정보/TIER2 */
  --pur: #a78bfa;    /* TIER3 */
  --warn: #fb923c;   /* 경고/OFF */
  --red: #f87171;    /* 위험/TIER4 */
  --tx: #dde4f0;
  --tx2: #7a8499;
  --tx3: #2e3648;
}
```

---

## TIER 색상

```javascript
const TC = {
  TIER1: '#4ade80',
  TIER2: '#60a5fa',
  TIER3: '#a78bfa',
  TIER4: '#f87171',
  LOW_VOLUME: '#6b7280',
  UNCLASSIFIED: '#8b5cf6',
};
```

---

## 폰트

- 본문: `Noto Sans KR` (Google Fonts CDN)
- 숫자: `DM Mono` (Google Fonts CDN)

---

## Chart.js 공통 설정 (4.4.x)

```javascript
const ax = {
  grid: { color: 'rgba(255,255,255,.04)' },
  ticks: { color: '#2e3648', font: { size: 10 } }
};

const tt = {
  backgroundColor: '#11141c',
  titleColor: '#dde4f0',
  bodyColor: '#7a8499',
  borderColor: '#1c2030',
  borderWidth: 1
};
```
