"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, TrendingDown, Eye, AlertCircle, CheckCircle } from "lucide-react";
import { formatRelativeDate } from "@/lib/utils";
import { api } from "@/lib/api";

// Mock data — conectar a endpoint real de actividad
const MOCK_ACTIVITIES = [
  {
    id: 1,
    type: "new_property",
    message: "Nueva propiedad en La Barra — Casa 4 dorm con piscina",
    detail: "USD 780,000",
    time: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    source: "infocasas",
  },
  {
    id: 2,
    type: "price_drop",
    message: "Bajada de precio — Apto 3 dorm Punta del Este Centro",
    detail: "USD 450,000 → USD 390,000 (-13%)",
    time: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    source: "mercadolibre",
  },
  {
    id: 3,
    type: "scraping",
    message: "Scraping completado — MercadoLibre",
    detail: "234 propiedades encontradas, 12 nuevas",
    time: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    source: "system",
  },
  {
    id: 4,
    type: "opportunity",
    message: "Oportunidad detectada — Terreno José Ignacio 2000m²",
    detail: "USD 350,000 — 18% debajo del mercado",
    time: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    source: "ai",
  },
  {
    id: 5,
    type: "new_property",
    message: "Nueva propiedad en Manantiales — Chacra 5ha",
    detail: "USD 1,200,000",
    time: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    source: "gallito",
  },
];

const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  new_property: <Building2 className="h-3.5 w-3.5 text-brand-500" />,
  price_drop: <TrendingDown className="h-3.5 w-3.5 text-red-500" />,
  opportunity: <Eye className="h-3.5 w-3.5 text-amber-500" />,
  scraping: <CheckCircle className="h-3.5 w-3.5 text-green-500" />,
  error: <AlertCircle className="h-3.5 w-3.5 text-red-500" />,
};

const ACTIVITY_COLORS: Record<string, string> = {
  new_property: "bg-brand-50 dark:bg-brand-950",
  price_drop: "bg-red-50 dark:bg-red-950/20",
  opportunity: "bg-amber-50 dark:bg-amber-950/20",
  scraping: "bg-green-50 dark:bg-green-950/20",
  error: "bg-red-50 dark:bg-red-950/20",
};

export function RecentActivity() {
  return (
    <div className="divide-y">
      {MOCK_ACTIVITIES.map((activity) => (
        <div key={activity.id} className="flex items-start gap-3 px-4 py-3 hover:bg-muted/30 transition-colors">
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
              ACTIVITY_COLORS[activity.type] || "bg-muted"
            }`}
          >
            {ACTIVITY_ICONS[activity.type]}
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-foreground">{activity.message}</p>
            <p className="text-xs text-muted-foreground">{activity.detail}</p>
          </div>

          <div className="text-right flex-shrink-0">
            <p className="text-xs text-muted-foreground whitespace-nowrap">
              {formatRelativeDate(activity.time)}
            </p>
            <p className="text-xs text-muted-foreground/60 mt-0.5">{activity.source}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
