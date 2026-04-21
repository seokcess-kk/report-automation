import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 시맨틱 색상 — CSS 변수에서 실제 값 읽음 (globals.css)
        bg: 'rgb(var(--bg) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        elevated: 'rgb(var(--elevated) / <alpha-value>)',
        border: 'rgb(var(--border) / <alpha-value>)',
        'border-strong': 'rgb(var(--border-strong) / <alpha-value>)',
        fg: 'rgb(var(--fg) / <alpha-value>)',
        muted: 'rgb(var(--muted) / <alpha-value>)',
        subtle: 'rgb(var(--subtle) / <alpha-value>)',
        accent: 'rgb(var(--accent) / <alpha-value>)',
        'accent-soft': 'rgb(var(--accent-soft) / <alpha-value>)',
        'accent-strong': 'rgb(var(--accent-strong) / <alpha-value>)',
        success: 'rgb(var(--success) / <alpha-value>)',
        'success-soft': 'rgb(var(--success-soft) / <alpha-value>)',
        warn: 'rgb(var(--warn) / <alpha-value>)',
        'warn-soft': 'rgb(var(--warn-soft) / <alpha-value>)',
        danger: 'rgb(var(--danger) / <alpha-value>)',
        'danger-soft': 'rgb(var(--danger-soft) / <alpha-value>)',
        info: 'rgb(var(--info) / <alpha-value>)',
        'info-soft': 'rgb(var(--info-soft) / <alpha-value>)',

        // 하위 호환 (기존 컴포넌트 단계적 마이그레이션용)
        brand: {
          bg: 'rgb(var(--bg) / <alpha-value>)',
          card: 'rgb(var(--surface) / <alpha-value>)',
          border: 'rgb(var(--border) / <alpha-value>)',
          primary: 'rgb(var(--accent) / <alpha-value>)',
          success: 'rgb(var(--success) / <alpha-value>)',
          warn: 'rgb(var(--warn) / <alpha-value>)',
          danger: 'rgb(var(--danger) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: [
          '"Pretendard Variable"', 'Pretendard',
          '-apple-system', 'BlinkMacSystemFont',
          'system-ui', 'Roboto', '"Helvetica Neue"',
          '"Segoe UI"', '"Apple SD Gothic Neo"',
          '"Noto Sans KR"', '"Malgun Gothic"',
          'sans-serif',
        ],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],    // 11px
        xs: ['0.75rem', { lineHeight: '1.125rem' }],     // 12px
        sm: ['0.875rem', { lineHeight: '1.375rem' }],    // 14px
        base: ['1rem', { lineHeight: '1.5rem' }],        // 16px
        lg: ['1.125rem', { lineHeight: '1.625rem' }],    // 18px
        xl: ['1.25rem', { lineHeight: '1.75rem' }],      // 20px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],       // 24px
        '3xl': ['2rem', { lineHeight: '2.5rem' }],       // 32px
      },
      borderRadius: {
        DEFAULT: '6px',
        md: '8px',
        lg: '12px',
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgb(0 0 0 / 0.2)',
        card: '0 2px 8px -2px rgb(0 0 0 / 0.3), 0 1px 3px 0 rgb(0 0 0 / 0.15)',
        raised: '0 8px 24px -4px rgb(0 0 0 / 0.35), 0 4px 8px -2px rgb(0 0 0 / 0.2)',
        drawer: '-16px 0 40px -8px rgb(0 0 0 / 0.5)',
      },
      transitionTimingFunction: {
        swift: 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
};
export default config;
