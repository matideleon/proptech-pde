/** @type {import('next').NextConfig} */
const nextConfig = {
  // Output standalone para imágenes Docker chicas (server.js autocontenido)
  output: "standalone",
  // No redirigir (308) las barras finales: dejamos que /api/v1/properties/
  // pase tal cual al backend. Si Next quita la barra, FastAPI la vuelve a
  // agregar (307) con el host interno api:8000 → loop + URL inalcanzable.
  skipTrailingSlashRedirect: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.mlstatic.com" },
      { protocol: "https", hostname: "**.infocasas.com.uy" },
      { protocol: "https", hostname: "**.gallito.com.uy" },
      { protocol: "https", hostname: "**.fbsbx.com" },
      { protocol: "https", hostname: "**.fbcdn.net" },
      { protocol: "https", hostname: "**.fna.fbcdn.net" },
      { protocol: "https", hostname: "picsum.photos" },
      { protocol: "https", hostname: "images.unsplash.com" },
      { protocol: "https", hostname: "**.supabase.co" },
    ],
  },
  async rewrites() {
    // Proxy del API por Next.js: el navegador solo habla con el dominio del
    // frontend. Next reenvía /api/v1/* al backend.
    //  - Local/dev:   http://127.0.0.1:8000
    //  - Docker/Easypanel: http://api:8000 (vía BACKEND_INTERNAL_URL)
    const backend = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backend}/api/v1/:path*`,
      },
    ];
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts"],
  },
};

module.exports = nextConfig;
