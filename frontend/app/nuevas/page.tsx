"use client";

export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { DashboardLayout } from "@/components/admin/DashboardLayout";
import { PropertyCard } from "@/components/properties/PropertyCard";
import { propertiesApi } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

function NuevasContent() {
  const { data, isLoading } = useQuery({
    queryKey: ["nuevas-properties"],
    queryFn: () =>
      propertiesApi
        .list({ sort_by: "created_at", sort_order: "desc", page_size: 100, days_ago: 7 })
        .then((r) => r.data),
  });

  return (
    <DashboardLayout>
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-brand-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Nuevas propiedades</h1>
            <p className="text-sm text-muted-foreground">
              {isLoading
                ? "Cargando..."
                : `${formatNumber(data?.total)} propiedades en los últimos 7 días`}
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {[...Array(12)].map((_, i) => (
              <div key={i} className="h-80 skeleton rounded-xl" />
            ))}
          </div>
        ) : data?.items?.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
              <Sparkles className="h-8 w-8 text-muted-foreground/50" />
            </div>
            <h3 className="font-semibold mb-1">Sin propiedades nuevas</h3>
            <p className="text-sm text-muted-foreground">
              Todavia no hay propiedades para mostrar.
            </p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {data?.items?.map((property: any) => (
              <PropertyCard key={property.id} property={property} variant="default" />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

export default function NuevasPage() {
  return (
    <Suspense fallback={null}>
      <NuevasContent />
    </Suspense>
  );
}
