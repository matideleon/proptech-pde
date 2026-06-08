import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formatear moneda.
 * @example formatCurrency(250000, "USD") → "USD 250,000"
 */
export function formatCurrency(
  value: number | undefined | null,
  currency: string = "USD",
  compact: boolean = false
): string {
  if (value == null) return "Consultar";

  if (compact && value >= 1_000_000) {
    return `${currency} ${(value / 1_000_000).toFixed(1)}M`;
  }
  if (compact && value >= 1_000) {
    return `${currency} ${(value / 1_000).toFixed(0)}K`;
  }

  return `${currency} ${value.toLocaleString("es-UY", { maximumFractionDigits: 0 })}`;
}

/**
 * Formatear número con separadores.
 */
export function formatNumber(value: number | undefined | null): string {
  if (value == null) return "—";
  return value.toLocaleString("es-UY");
}

/**
 * Formatear área en m².
 */
export function formatArea(value: number | undefined | null): string {
  if (value == null) return "—";
  return `${value.toLocaleString("es-UY", { maximumFractionDigits: 0 })} m²`;
}

/**
 * Obtener color según score de IA (0-100).
 */
export function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600 dark:text-green-400";
  if (score >= 60) return "text-yellow-600 dark:text-yellow-400";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

/**
 * Obtener label del tipo de propiedad.
 */
export function getPropertyTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    apartamento: "Apartamento",
    casa: "Casa",
    terreno: "Terreno",
    penthouse: "Penthouse",
    duplex: "Dúplex",
    chacra: "Chacra",
    campo: "Campo",
    local_comercial: "Local Comercial",
    oficina: "Oficina",
    garage: "Garage",
    hotel: "Hotel",
    otro: "Propiedad",
  };
  return labels[type] || type;
}

/**
 * Calcular días desde una fecha.
 */
export function getDaysAgo(dateStr: string): number {
  const date = new Date(dateStr);
  const now = new Date();
  return Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * Formatear fecha relativa.
 */
export function formatRelativeDate(dateStr: string): string {
  const days = getDaysAgo(dateStr);
  if (days === 0) return "Hoy";
  if (days === 1) return "Ayer";
  if (days < 7) return `Hace ${days} días`;
  if (days < 30) return `Hace ${Math.floor(days / 7)} semanas`;
  if (days < 365) return `Hace ${Math.floor(days / 30)} meses`;
  return `Hace ${Math.floor(days / 365)} años`;
}

/**
 * Truncar texto con ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

/**
 * Capitalizar primera letra.
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Generar avatar placeholder con iniciales.
 */
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}
