"use client";

/**
 * Hook de toasts minimalista (patrón shadcn/ui).
 * Estado en memoria con un store simple basado en listeners.
 */
import * as React from "react";

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "destructive" | "success";
  duration?: number;
}

type Listener = (toasts: Toast[]) => void;

let toasts: Toast[] = [];
const listeners = new Set<Listener>();

function emit() {
  listeners.forEach((l) => l([...toasts]));
}

export function toast(t: Omit<Toast, "id">) {
  const id = Math.random().toString(36).slice(2);
  const newToast: Toast = { id, duration: 4000, variant: "default", ...t };
  toasts = [...toasts, newToast];
  emit();

  if (newToast.duration && newToast.duration > 0) {
    setTimeout(() => dismiss(id), newToast.duration);
  }
  return id;
}

export function dismiss(id: string) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

export function useToast() {
  const [items, setItems] = React.useState<Toast[]>(toasts);

  React.useEffect(() => {
    listeners.add(setItems);
    return () => {
      listeners.delete(setItems);
    };
  }, []);

  return { toasts: items, toast, dismiss };
}
