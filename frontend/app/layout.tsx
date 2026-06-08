import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "PropTech PDE — Inteligencia Inmobiliaria Punta del Este",
    template: "%s | PropTech PDE",
  },
  description:
    "Plataforma de inteligencia inmobiliaria para Punta del Este. Encuentra propiedades, analiza el mercado y detecta oportunidades con IA.",
  keywords: ["punta del este", "inmuebles", "propiedades", "uruguay", "real estate", "maldonado"],
  authors: [{ name: "PropTech PDE" }],
  openGraph: {
    type: "website",
    locale: "es_UY",
    url: "https://proptech.uy",
    siteName: "PropTech PDE",
    title: "PropTech PDE — Inteligencia Inmobiliaria",
    description: "La plataforma más avanzada de análisis inmobiliario de Punta del Este",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0ea5e9",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-background text-foreground`}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
