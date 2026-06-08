"use client";

import { X, CheckCircle, AlertCircle, Info } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const ICONS = {
  default: <Info className="h-4 w-4 text-brand-500" />,
  success: <CheckCircle className="h-4 w-4 text-emerald-500" />,
  destructive: <AlertCircle className="h-4 w-4 text-red-500" />,
};

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-full max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "flex items-start gap-3 bg-card border shadow-lg rounded-xl p-4 animate-slide-in",
            t.variant === "destructive" && "border-red-200 dark:border-red-900",
            t.variant === "success" && "border-emerald-200 dark:border-emerald-900"
          )}
        >
          <div className="mt-0.5">{ICONS[t.variant || "default"]}</div>
          <div className="flex-1 min-w-0">
            {t.title && <p className="text-sm font-medium text-foreground">{t.title}</p>}
            {t.description && (
              <p className="text-xs text-muted-foreground mt-0.5">{t.description}</p>
            )}
          </div>
          <button onClick={() => dismiss(t.id)} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
