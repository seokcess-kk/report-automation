import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: '#0f172a',
          card: '#1e293b',
          border: '#334155',
          primary: '#60a5fa',
          success: '#4ade80',
          warn: '#f59e0b',
          danger: '#f87171',
        },
      },
    },
  },
  plugins: [],
};
export default config;
