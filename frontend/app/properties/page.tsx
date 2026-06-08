"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import {
  SlidersHorizontal,
  Grid3X3,
  Map,
  List,
  Search,
  X,
  ChevronDown,
} from "lucide-react";
import { DashboardLayout } from "@/components/admin/DashboardLayout";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { PropertyFilters } from "@/components/properties/PropertyFilters";
import { MarketMap } from "@/components/maps/MarketMap";
import { api, propertiesApi } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

type ViewMode = "grid" | "list" | "map";

const SORT_OPTIONS = [
  { value: "created_at:desc", label: "Más recientes" },
  { value: "price:asc", label: "Precio: menor a mayor" },
  { value: "price:desc", label: "Precio: mayor a menor" },
  { value: "ai_score:desc", label: "Score IA: mayor a menor" },
  { value: "area_total:desc", label: "Superficie: mayor a menor" },
  { value: "price_per_m2_usd:asc", label: "Precio/m²: menor a mayor" },
];

export default function PropertiesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [showFilters, setShowFilters] = useState(false);
  const [sort, setSort] = useState("created_at:desc");

  // Filtros desde URL params
  const filters = {
    q: searchParams.get("q") || undefined,
    operation: searchParams.get("operation") || undefined,
    property_type: searchParams.getAll("property_type") || undefined,
    price_min: searchParams.get("price_min") ? Number(searchParams.get("price_min")) : undefined,
    price_max: searchParams.get("price_max") ? Number(searchParams.get("price_max")) : undefined,
    bedrooms_min: searchParams.get("bedrooms_min") ? Number(searchParams.get("bedrooms_min")) : undefined,
    bathrooms_min: searchParams.get("bathrooms_min") ? Number(searchParams.get("bathrooms_min")) : undefined,
    neighborhood: searchParams.getAll("neighborhood") || undefined,
    ai_premium: searchParams.get("ai_premium") === "true" ? true : undefined,
    ai_opportunity: searchParams.get("ai_opportunity") === "true" ? true : undefined,
    page: Number(searchParams.get("page") || 1),
    page_size: 24,
    sort_by: sort.split(":")[0],
    sort_order: sort.split(":")[1],
  };

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["properties", filters],
    queryFn: () => propertiesApi.list(filters).then((r) => r.data),
  });

  const activeFiltersCount = [
    filters.q,
    filters.operation,
    filters.property_type?.length,
    filters.price_min,
    filters.price_max,
    filters.bedrooms_min,
    filters.bathrooms_min,
    filters.neighborhood?.length,
    filters.ai_premium,
    filters.ai_opportunity,
  ].filter(Boolean).length;

  const updateFilter = useCallback(
    (key: string, value: any) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value === undefined || value === null || value === "") {
        params.delete(key);
      } else if (Array.isArray(value)) {
        params.delete(key);
        value.forEach((v) => params.append(key, v));
      } else {
        params.set(key, String(value));
      }
      params.set("page", "1");
      router.push(`/properties?${params.toString()}`);
    },
    [searchParams, router]
  );

  const clearFilters = () => {
    router.push("/properties");
  };

  return (
    <DashboardLayout>
      <div className="space-y-4 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">Propiedades</h1>
            <p className="text-sm text-muted-foreground">
              {isLoading ? "Cargando..." : `${formatNumber(data?.total)} propiedades encontradas`}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Sort */}
            <div className="relative">
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                className="appearance-none bg-card border rounded-lg px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
            </div>

            {/* Filters button */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 bg-card border rounded-lg px-3 py-2 text-sm hover:bg-muted transition-colors"
            >
              <SlidersHorizontal className="h-4 w-4" />
              Filtros
              {activeFiltersCount > 0 && (
                <span className="w-5 h-5 bg-brand-500 text-white rounded-full text-xs flex items-center justify-center">
                  {activeFiltersCount}
                </span>
              )}
            </button>

            {/* View modes */}
            <div className="flex items-center gap-1 bg-card border rounded-lg p-1">
              {([
                ["grid", Grid3X3],
                ["list", List],
                ["map", Map],
              ] as const).map(([mode, Icon]) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`p-1.5 rounded ${viewMode === mode ? "bg-brand-500 text-white" : "text-muted-foreground hover:text-foreground"}`}
                >
                  <Icon className="h-4 w-4" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Search bar */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por título, barrio, características..."
            defaultValue={filters.q}
            onChange={(e) => {
              const v = e.target.value;
              if (v.length === 0 || v.length >= 3) {
                setTimeout(() => updateFilter("q", v || undefined), 300);
              }
            }}
            className="w-full pl-9 pr-4 py-2.5 bg-card border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {filters.q && (
            <button
              onClick={() => updateFilter("q", undefined)}
              className="absolute right-3 top-2.5"
            >
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          )}
        </div>

        {/* Active filters */}
        {activeFiltersCount > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">Filtros activos:</span>
            {filters.operation && (
              <FilterBadge label={`Operación: ${filters.operation}`} onRemove={() => updateFilter("operation", undefined)} />
            )}
            {filters.price_min && (
              <FilterBadge label={`Desde USD ${formatNumber(filters.price_min)}`} onRemove={() => updateFilter("price_min", undefined)} />
            )}
            {filters.price_max && (
              <FilterBadge label={`Hasta USD ${formatNumber(filters.price_max)}`} onRemove={() => updateFilter("price_max", undefined)} />
            )}
            {filters.ai_premium && (
              <FilterBadge label="Solo Premium" onRemove={() => updateFilter("ai_premium", undefined)} />
            )}
            {filters.ai_opportunity && (
              <FilterBadge label="Solo Oportunidades" onRemove={() => updateFilter("ai_opportunity", undefined)} />
            )}
            <button onClick={clearFilters} className="text-xs text-red-500 hover:underline">
              Limpiar todo
            </button>
          </div>
        )}

        {/* Filters panel */}
        {showFilters && (
          <PropertyFilters
            filters={filters}
            onFilterChange={updateFilter}
            onClose={() => setShowFilters(false)}
          />
        )}

        {/* Content */}
        {viewMode === "map" ? (
          <div className="rounded-xl border overflow-hidden" style={{ height: 600 }}>
            <MarketMap />
          </div>
        ) : (
          <>
            {isLoading ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {[...Array(12)].map((_, i) => (
                  <div key={i} className="h-80 skeleton rounded-xl" />
                ))}
              </div>
            ) : data?.items?.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                  <Search className="h-8 w-8 text-muted-foreground/50" />
                </div>
                <h3 className="font-semibold mb-1">Sin resultados</h3>
                <p className="text-sm text-muted-foreground">
                  No hay propiedades que coincidan con los filtros actuales.
                </p>
                <button onClick={clearFilters} className="mt-4 text-sm text-brand-500 hover:underline">
                  Limpiar filtros
                </button>
              </div>
            ) : (
              <div className={viewMode === "grid"
                ? "grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                : "flex flex-col gap-3"
              }>
                {data?.items?.map((property: any) => (
                  <PropertyCard
                    key={property.id}
                    property={property}
                    variant={viewMode === "list" ? "horizontal" : "default"}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {data && data.pages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <button
                  disabled={filters.page <= 1}
                  onClick={() => updateFilter("page", filters.page - 1)}
                  className="px-3 py-1.5 text-sm bg-card border rounded-lg disabled:opacity-50 hover:bg-muted"
                >
                  Anterior
                </button>
                <span className="text-sm text-muted-foreground">
                  Página {filters.page} de {data.pages}
                </span>
                <button
                  disabled={filters.page >= data.pages}
                  onClick={() => updateFilter("page", filters.page + 1)}
                  className="px-3 py-1.5 text-sm bg-card border rounded-lg disabled:opacity-50 hover:bg-muted"
                >
                  Siguiente
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}

function FilterBadge({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-300 text-xs px-2 py-0.5 rounded-full">
      {label}
      <button onClick={onRemove}>
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}
