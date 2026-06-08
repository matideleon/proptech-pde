"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number | undefined;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: React.ReactNode;
  loading?: boolean;
  highlight?: boolean;
}

export function StatCard({
  title,
  value,
  change,
  changeType = "neutral",
  icon,
  loading = false,
  highlight = false,
}: StatCardProps) {
  const changeIcon =
    changeType === "positive" ? (
      <TrendingUp className="h-3 w-3" />
    ) : changeType === "negative" ? (
      <TrendingDown className="h-3 w-3" />
    ) : (
      <Minus className="h-3 w-3" />
    );

  const changeColor =
    changeType === "positive"
      ? "text-emerald-600 dark:text-emerald-400"
      : changeType === "negative"
      ? "text-red-500"
      : "text-muted-foreground";

  if (loading) {
    return (
      <div className="bg-card rounded-xl border shadow-card p-4">
        <div className="h-4 w-24 skeleton rounded mb-3" />
        <div className="h-7 w-32 skeleton rounded mb-2" />
        <div className="h-3 w-20 skeleton rounded" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "bg-card rounded-xl border shadow-card p-4 transition-all hover:shadow-card-hover",
        highlight && "border-brand-200 dark:border-brand-800 bg-gradient-to-br from-brand-50/50 to-transparent dark:from-brand-950/50"
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-muted-foreground font-medium">{title}</p>
        {icon && (
          <div
            className={cn(
              "w-7 h-7 rounded-lg flex items-center justify-center",
              highlight ? "bg-brand-100 text-brand-600 dark:bg-brand-900 dark:text-brand-400" : "bg-muted text-muted-foreground"
            )}
          >
            {icon}
          </div>
        )}
      </div>

      <p className="text-2xl font-bold text-foreground leading-none mb-1.5">
        {value ?? "—"}
      </p>

      {change && (
        <div className={cn("flex items-center gap-1 text-xs", changeColor)}>
          {changeIcon}
          <span>{change}</span>
        </div>
      )}
    </div>
  );
}
