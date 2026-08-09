import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  output: "standalone",
  // Fija la raíz de trazado al directorio del proyecto (no al padre) para que
  // el servidor standalone se genere en `.next/standalone/server.js` y no
  // anidado en una subcarpeta (evita "MODULE_NOT_FOUND" al hacer `npm run start`).
  outputFileTracingRoot: process.cwd(),
  typescript: {
    ignoreBuildErrors: false,
  },
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default withNextIntl(nextConfig);