"use client";

import { X, Star, Sparkles } from "lucide-react";

const PROPERTY_TYPES = [
  { value: "apartamento", label: "Apartamento" },
  { value: "casa", label: "Casa" },
  { value: "terreno", label: "Terreno" },
  { value: "penthouse", label: "Penthouse" },
  { value: "duplex", label: "Dúplex" },
  { value: "chacra", label: "Chacra" },
  { value: "campo", label: "Campo" },
  { value: "local_comercial", label: "Local Comercial" },
];

const NEIGHBORHOODS = [
  "Punta del Este Centro",
  "La Barra",
  "José Ignacio",
  "Manantiales",
  "Punta Ballena",
  "Cantegril",
  "Pinares",
  "Beverly Hills",
  "San Rafael",
  "Maldonado Centro",
  "El Chorro",
  "Montoya",
  "Solanas",
  "Aidy Grill",
  "Roosevelt",
];

// Rangos de precio orientados a ALQUILER (USD/mes)
const PRICE_RANGES = [
  { label: "400 - 700", min: 400, max: 700 },
  { label: "700 - 1.200", min: 700, max: 1200 },
  { label: "1.200 - 2.000", min: 1200, max: 2000 },
];

// Opciones de los selects de cuartos / baños
const ROOM_OPTIONS = [
  { value: undefined, label: "Cualquiera" },
  { value: 1, label: "1 o más" },
  { value: 2, label: "2 o más" },
  { value: 3, label: "3 o más" },
  { value: 4, label: "4 o más" },
  { value: 5, label: "5 o más" },
];

interface PropertyFiltersProps {
  filters: any;
  onFilterChange: (key: string, value: any) => void;
  onClose: () => void;
}

export function PropertyFilters({ filters, onFilterChange, onClose }: PropertyFiltersProps) {
  return (
    <div className="bg-card border rounded-xl p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">Filtros avanzados</h3>
        <button onClick={onClose}>
          <X className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">

        {/* Operación */}
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-2 block">Operación</label>
          <div className="flex gap-2">
            {[
              { value: undefined, label: "Todas" },
              { value: "venta", label: "Venta" },
              { value: "alquiler", label: "Alquiler" },
            ].map((opt) => (
              <button
                key={String(opt.value)}
                onClick={() => onFilterChange("operation", opt.value)}
                className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors ${
                  filters.operation === opt.value
                    ? "bg-brand-500 text-white border-brand-500"
                    : "hover:bg-muted"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Precio */}
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-2 block">Rango de precio</label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="Mín USD"
              value={filters.price_min || ""}
              onChange={(e) => onFilterChange("price_min", e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-2 py-1.5 text-xs bg-muted rounded-lg border-0 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            <input
              type="number"
              placeholder="Máx USD"
              value={filters.price_max || ""}
              onChange={(e) => onFilterChange("price_max", e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-2 py-1.5 text-xs bg-muted rounded-lg border-0 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          {/* Presets rápidos */}
          <div className="flex flex-wrap gap-1 mt-1.5">
            {PRICE_RANGES.slice(0, 3).map((range) => (
              <button
                key={range.label}
                onClick={() => {
                  onFilterChange("price_min", range.min);
                  onFilterChange("price_max", range.max);
                }}
                className="text-xs text-brand-500 hover:underline"
              >
                {range.label.replace("USD ", "")}
              </button>
            ))}
          </div>
        </div>

        {/* Dormitorios y Baños (selects) */}
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-2 block">Cuartos y baños</label>
          <div className="grid grid-cols-2 gap-2">
            {/* Select de dormitorios */}
            <select
              value={filters.bedrooms_min ?? ""}
              onChange={(e) =>
                onFilterChange("bedrooms_min", e.target.value ? Number(e.target.value) : undefined)
              }
              className="w-full px-2 py-1.5 text-xs bg-muted rounded-lg border-0 focus:outline-none focus:ring-1 focus:ring-brand-500 cursor-pointer"
              aria-label="Dormitorios"
            >
              {ROOM_OPTIONS.map((opt) => (
                <option key={`bed-${opt.value}`} value={opt.value ?? ""}>
                  {opt.value === undefined ? "🛏 Dormitorios" : `🛏 ${opt.label}`}
                </option>
              ))}
            </select>

            {/* Select de baños */}
            <select
              value={filters.bathrooms_min ?? ""}
              onChange={(e) =>
                onFilterChange("bathrooms_min", e.target.value ? Number(e.target.value) : undefined)
              }
              className="w-full px-2 py-1.5 text-xs bg-muted rounded-lg border-0 focus:outline-none focus:ring-1 focus:ring-brand-500 cursor-pointer"
              aria-label="Baños"
            >
              {ROOM_OPTIONS.map((opt) => (
                <option key={`bath-${opt.value}`} value={opt.value ?? ""}>
                  {opt.value === undefined ? "🚿 Baños" : `🚿 ${opt.label}`}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* IA Filters */}
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-2 block">Clasificación IA</label>
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!filters.ai_premium}
                onChange={(e) => onFilterChange("ai_premium", e.target.checked ? true : undefined)}
                className="rounded border-muted-foreground"
              />
              <Star className="h-3 w-3 text-amber-500" />
              <span className="text-xs">Solo Premium</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!filters.ai_opportunity}
                onChange={(e) => onFilterChange("ai_opportunity", e.target.checked ? true : undefined)}
                className="rounded"
              />
              <Sparkles className="h-3 w-3 text-emerald-500" />
              <span className="text-xs">Solo Oportunidades</span>
            </label>
          </div>
        </div>
      </div>

      {/* Tipos de propiedad */}
      <div>
        <label className="text-xs font-medium text-muted-foreground mb-2 block">Tipo de propiedad</label>
        <div className="flex flex-wrap gap-2">
          {PROPERTY_TYPES.map((type) => {
            const isSelected = (filters.property_type || []).includes(type.value);
            return (
              <button
                key={type.value}
                onClick={() => {
                  const current = filters.property_type || [];
                  const updated = isSelected
                    ? current.filter((t: string) => t !== type.value)
                    : [...current, type.value];
                  onFilterChange("property_type", updated.length > 0 ? updated : undefined);
                }}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  isSelected
                    ? "bg-brand-500 text-white border-brand-500"
                    : "hover:bg-muted"
                }`}
              >
                {type.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Zonas */}
      <div>
        <label className="text-xs font-medium text-muted-foreground mb-2 block">Barrios / Zonas</label>
        <div className="flex flex-wrap gap-2">
          {NEIGHBORHOODS.map((nb) => {
            const isSelected = (filters.neighborhood || []).includes(nb);
            return (
              <button
                key={nb}
                onClick={() => {
                  const current = filters.neighborhood || [];
                  const updated = isSelected
                    ? current.filter((n: string) => n !== nb)
                    : [...current, nb];
                  onFilterChange("neighborhood", updated.length > 0 ? updated : undefined);
                }}
                className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                  isSelected
                    ? "bg-brand-500 text-white border-brand-500"
                    : "hover:bg-muted"
                }`}
              >
                {nb}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
