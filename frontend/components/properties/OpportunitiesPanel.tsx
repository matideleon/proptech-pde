"use client";

import { TrendingDown, Sparkles, ExternalLink } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import Link from "next/link";

interface OpportunitiesPanelProps {
  opportunities?: any[];
  loading?: boolean;
}

export function OpportunitiesPanel({ opportunities, loading }: OpportunitiesPanelProps) {
  if (loading) {
    return (
      <div className="p-3 space-y-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-16 skeleton rounded-lg" />
        ))}
      </div>
    );
  }

  if (!opportunities?.length) {
    return (
      <div className="p-6 text-center text-sm text-muted-foreground">
        No hay oportunidades detectadas actualmente
      </div>
    );
  }

  return (
    <div className="divide-y">
      {opportunities.slice(0, 6).map((prop: any) => (
        <Link key={prop.id} href={`/properties/${prop.id}`}>
          <div className="px-4 py-3 hover:bg-muted/50 transition-colors cursor-pointer">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate text-foreground">
                  {prop.title}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  📍 {prop.neighborhood || prop.city}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-xs font-bold text-foreground">
                  {formatCurrency(prop.price_usd || prop.price, "USD", true)}
                </p>
                {prop.price_vs_market_pct && prop.price_vs_market_pct < 0 && (
                  <p className="text-xs text-emerald-500 flex items-center gap-0.5 justify-end">
                    <TrendingDown className="h-2.5 w-2.5" />
                    {Math.abs(prop.price_vs_market_pct).toFixed(0)}% menos
                  </p>
                )}
              </div>
            </div>

            {prop.ai_score && (
              <div className="mt-1 flex items-center gap-2">
                <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 rounded-full"
                    style={{ width: `${prop.ai_score}%` }}
                  />
                </div>
                <span className="text-xs text-muted-foreground">{prop.ai_score.toFixed(0)}</span>
              </div>
            )}
          </div>
        </Link>
      ))}

      <div className="px-4 py-2">
        <Link href="/properties?ai_opportunity=true" className="text-xs text-brand-500 hover:underline flex items-center gap-1">
          Ver todas las oportunidades
          <ExternalLink className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
