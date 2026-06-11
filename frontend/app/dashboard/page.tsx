"use client";

import { Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  TrendingDown,
  TrendingUp,
  Sparkles,
  AlertCircle,
  MapPin,
  Activity,
  DollarSign,
} from "lucide-react";

import { DashboardLayout } from "@/components/admin/DashboardLayout";
import { StatCard } from "@/components/admin/StatCard";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { PriceChart } from "@/components/charts/PriceChart";
import { HeatmapZones } from "@/components/charts/HeatmapZones";
import { MarketMap } from "@/components/maps/MarketMap";
import { OpportunitiesPanel } from "@/components/properties/OpportunitiesPanel";
import { RecentActivity } from "@/components/admin/RecentActivity";
import { api } from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/utils";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["market-stats"],
    queryFn: () => api.get("/properties/stats").then((r) => r.data),
    refetchInterval: 5 * 60 * 1000, // Refrescar cada 5 min
  });

  const { data: opportunities, isLoading: oppLoading } = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.get("/properties/opportunities?limit=6").then((r) => r.data),
  });

  const { data: recentProperties } = useQuery({
    queryKey: ["recent-properties"],
    queryFn: () =>
      api.get("/properties?sort_by=created_at&sort_order=desc&page_size=6&status=active").then((r) => r.data),
  });

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Dashboard de Mercado
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Punta del Este · Maldonado, Uruguay — Tiempo real
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted px-3 py-1.5 rounded-full">
            <Activity className="h-3 w-3 text-green-500 animate-pulse" />
            Actualizado hace 2 min
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Propiedades Activas"
            value={formatNumber(stats?.active_properties)}
            change="+23 hoy"
            changeType="positive"
            icon={<Building2 className="h-4 w-4" />}
            loading={statsLoading}
          />
          <StatCard
            title="Precio Promedio Venta"
            value={formatCurrency(stats?.avg_price_sale_usd, "USD")}
            change="+2.3% mes"
            changeType="positive"
            icon={<DollarSign className="h-4 w-4" />}
            loading={statsLoading}
          />
          <StatCard
            title="Precio por m²"
            value={formatCurrency(stats?.avg_price_m2_usd, "USD") + "/m²"}
            change="-0.8% mes"
            changeType="negative"
            icon={<MapPin className="h-4 w-4" />}
            loading={statsLoading}
          />
          <StatCard
            title="Oportunidades IA"
            value={formatNumber(stats?.opportunity_count)}
            change="Detectadas hoy"
            changeType="neutral"
            icon={<Sparkles className="h-4 w-4" />}
            loading={statsLoading}
            highlight
          />
        </div>

        {/* Segundo row: precio drops + premium */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Nuevas Esta Semana"
            value={formatNumber(stats?.new_this_week)}
            icon={<TrendingUp className="h-4 w-4" />}
            changeType="positive"
            loading={statsLoading}
          />
          <StatCard
            title="Bajas de Precio"
            value={formatNumber(stats?.price_drops_this_week)}
            change="Esta semana"
            icon={<TrendingDown className="h-4 w-4" />}
            changeType="negative"
            loading={statsLoading}
          />
          <StatCard
            title="Premium"
            value={formatNumber(stats?.premium_count)}
            change="Propiedades de lujo"
            icon={<Sparkles className="h-4 w-4" />}
            changeType="neutral"
            loading={statsLoading}
          />
          <StatCard
            title="Precio Alquiler Prom."
            value={formatCurrency(stats?.avg_price_rent_usd, "USD") + "/mes"}
            icon={<Activity className="h-4 w-4" />}
            changeType="neutral"
            loading={statsLoading}
          />
        </div>

        {/* Main content: Mapa + Oportunidades */}
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-card rounded-xl border shadow-card overflow-hidden" style={{ height: 420 }}>
              <div className="px-4 py-3 border-b flex items-center justify-between">
                <h2 className="font-semibold text-sm">Mapa de Mercado</h2>
                <div className="flex gap-1">
                  <button className="text-xs px-2 py-1 bg-primary text-primary-foreground rounded">Heatmap</button>
                  <button className="text-xs px-2 py-1 text-muted-foreground hover:bg-muted rounded">Clusters</button>
                </div>
              </div>
              <Suspense fallback={<div className="h-full skeleton" />}>
                <MarketMap properties={recentProperties?.items || []} mode="heatmap" />
              </Suspense>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-card rounded-xl border shadow-card">
              <div className="px-4 py-3 border-b">
                <h2 className="font-semibold text-sm flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  Oportunidades IA
                </h2>
              </div>
              <Suspense fallback={<div className="p-4 space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-16 skeleton rounded-lg" />)}</div>}>
                <OpportunitiesPanel opportunities={opportunities} loading={oppLoading} />
              </Suspense>
            </div>
          </div>
        </div>

        {/* Charts row */}
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="bg-card rounded-xl border shadow-card p-4">
            <h2 className="font-semibold text-sm mb-4">Evolución de Precios por Zona</h2>
            <Suspense fallback={<div className="h-48 skeleton rounded" />}>
              <PriceChart />
            </Suspense>
          </div>

          <div className="bg-card rounded-xl border shadow-card p-4">
            <h2 className="font-semibold text-sm mb-4">Precio/m² por Barrio</h2>
            <Suspense fallback={<div className="h-48 skeleton rounded" />}>
              <HeatmapZones data={stats?.by_zone} />
            </Suspense>
          </div>
        </div>

        {/* Propiedades recientes */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Propiedades Recientes</h2>
            <a href="/properties" className="text-sm text-primary hover:underline">
              Ver todas →
            </a>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentProperties?.items?.map((property: any) => (
              <PropertyCard key={property.id} property={property} />
            ))}
          </div>
        </div>

        {/* Actividad reciente */}
        <div className="bg-card rounded-xl border shadow-card">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-sm">Actividad del Sistema</h2>
          </div>
          <RecentActivity />
        </div>

      </div>
    </DashboardLayout>
  );
}
