"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import {
  Bed,
  Bath,
  Maximize2,
  MapPin,
  Star,
  TrendingDown,
  Sparkles,
  Building2,
  Heart,
  Clock,
} from "lucide-react";
import { motion } from "framer-motion";
import { cn, formatCurrency, formatNumber } from "@/lib/utils";

interface Property {
  id: string;
  title: string;
  price: number;
  price_usd: number;
  currency: string;
  price_per_m2_usd?: number;
  operation: string;
  property_type: string;
  bedrooms?: number;
  bathrooms?: number;
  area_total?: number;
  neighborhood?: string;
  city: string;
  main_image_url?: string;
  ai_score?: number;
  ai_premium: boolean;
  ai_opportunity: boolean;
  ai_undervalued: boolean;
  ai_tags?: string[];
  source: string;
  created_at: string;
  first_seen_at?: string;
}

interface PropertyCardProps {
  property: Property;
  variant?: "default" | "compact" | "horizontal";
  className?: string;
}

export function PropertyCard({
  property,
  variant = "default",
  className,
}: PropertyCardProps) {
  const [isFavorited, setIsFavorited] = useState(false);
  const [imageError, setImageError] = useState(false);

  const hoursAgo = property.first_seen_at
    ? (Date.now() - new Date(property.first_seen_at).getTime()) / 3_600_000
    : null;
  const timeLabel = hoursAgo === null
    ? null
    : hoursAgo < 1
    ? "hace menos de 1h"
    : hoursAgo < 24
    ? `hace ${Math.floor(hoursAgo)}h`
    : hoursAgo < 48
    ? "hace 1 día"
    : `hace ${Math.floor(hoursAgo / 24)} días`;
  const timeBadgeClass = hoursAgo !== null && hoursAgo < 24
    ? "bg-amber-400 text-amber-900"
    : "bg-slate-500/80 text-slate-100";

  const operationLabel =
    property.operation === "venta"
      ? "Venta"
      : property.operation === "alquiler"
      ? "Alquiler"
      : "Temp.";

  const operationColor =
    property.operation === "venta"
      ? "bg-brand-500 text-white"
      : property.operation === "alquiler"
      ? "bg-emerald-500 text-white"
      : "bg-purple-500 text-white";

  const propertyTypeLabel: Record<string, string> = {
    apartamento: "Apartamento",
    casa: "Casa",
    terreno: "Terreno",
    penthouse: "Penthouse",
    duplex: "Dúplex",
    chacra: "Chacra",
    campo: "Campo",
    local_comercial: "Local",
    oficina: "Oficina",
    garage: "Garage",
    otro: "Propiedad",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <Link href={`/properties/${property.id}`}>
        <div
          className={cn(
            "property-card group bg-card rounded-xl border shadow-card overflow-hidden cursor-pointer",
            className
          )}
        >
          {/* Image */}
          <div className="relative h-52 bg-muted overflow-hidden">
            {property.main_image_url && !imageError ? (
              <Image
                src={property.main_image_url}
                alt={property.title}
                fill
                className="object-cover transition-transform duration-300 group-hover:scale-105"
                onError={() => setImageError(true)}
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                unoptimized
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-muted">
                <Building2 className="h-12 w-12 text-muted-foreground/30" />
              </div>
            )}

            {/* Overlay badges */}
            <div className="absolute top-3 left-3 flex flex-col gap-1.5">
              <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", operationColor)}>
                {operationLabel}
              </span>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-background/80 backdrop-blur-sm text-foreground">
                {propertyTypeLabel[property.property_type] || "Propiedad"}
              </span>
              {timeLabel && (
                <span className={cn("flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full", timeBadgeClass)}>
                  <Clock className="h-2.5 w-2.5" />
                  {timeLabel}
                </span>
              )}
            </div>

            {/* AI Badges */}
            <div className="absolute top-3 right-3 flex flex-col gap-1.5 items-end">
              {property.ai_premium && (
                <span className="badge-premium flex items-center gap-1">
                  <Star className="h-2.5 w-2.5" />
                  Premium
                </span>
              )}
              {property.ai_opportunity && (
                <span className="badge-opportunity flex items-center gap-1">
                  <Sparkles className="h-2.5 w-2.5" />
                  Oportunidad
                </span>
              )}
              {property.ai_undervalued && (
                <span className="flex items-center gap-1 bg-blue-500 text-white text-xs font-semibold px-2 py-0.5 rounded-full">
                  <TrendingDown className="h-2.5 w-2.5" />
                  Subvaluada
                </span>
              )}
            </div>

            {/* Favorite button */}
            <button
              onClick={(e) => {
                e.preventDefault();
                setIsFavorited(!isFavorited);
              }}
              className="absolute bottom-3 right-3 w-8 h-8 rounded-full bg-background/80 backdrop-blur-sm flex items-center justify-center transition-colors hover:bg-background"
            >
              <Heart
                className={cn(
                  "h-4 w-4 transition-colors",
                  isFavorited ? "fill-red-500 text-red-500" : "text-muted-foreground"
                )}
              />
            </button>

            {/* AI Score */}
            {property.ai_score && (
              <div className="absolute bottom-3 left-3 bg-background/80 backdrop-blur-sm rounded-full px-2 py-0.5 flex items-center gap-1">
                <span className="text-xs text-muted-foreground">IA</span>
                <span
                  className={cn(
                    "text-xs font-bold",
                    property.ai_score >= 80
                      ? "text-green-500"
                      : property.ai_score >= 60
                      ? "text-yellow-500"
                      : "text-muted-foreground"
                  )}
                >
                  {property.ai_score.toFixed(0)}
                </span>
              </div>
            )}
          </div>

          {/* Content */}
          <div className="p-4">
            {/* Price */}
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-lg font-bold text-foreground">
                  {formatCurrency(property.price_usd || property.price, "USD")}
                </p>
                {property.price_per_m2_usd && (
                  <p className="text-xs text-muted-foreground">
                    {formatCurrency(property.price_per_m2_usd, "USD")}/m²
                  </p>
                )}
              </div>
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded capitalize">
                {property.source}
              </span>
            </div>

            {/* Title */}
            <h3 className="text-sm font-medium text-foreground line-clamp-2 mb-2 group-hover:text-primary transition-colors">
              {property.title}
            </h3>

            {/* Location */}
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-3">
              <MapPin className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">
                {property.neighborhood
                  ? `${property.neighborhood}, ${property.city}`
                  : property.city}
              </span>
            </div>

            {/* Features */}
            <div className="flex items-center gap-3 text-xs text-muted-foreground border-t pt-3">
              {property.bedrooms != null && (
                <span className="flex items-center gap-1">
                  <Bed className="h-3 w-3" />
                  {property.bedrooms} dorm
                </span>
              )}
              {property.bathrooms != null && (
                <span className="flex items-center gap-1">
                  <Bath className="h-3 w-3" />
                  {property.bathrooms} baños
                </span>
              )}
              {property.area_total != null && (
                <span className="flex items-center gap-1">
                  <Maximize2 className="h-3 w-3" />
                  {formatNumber(property.area_total)} m²
                </span>
              )}
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
