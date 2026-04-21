/** @type {import('next').NextConfig} */
const nextConfig = {
  // 데이터 파일은 ../output/ 에 존재 → 빌드 시 fs로 직접 읽음 (서버 컴포넌트)
  experimental: {
    // 외부 디렉토리 접근 허용
  },
};

module.exports = nextConfig;
