"use client";

import Link from "next/link";
import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  MapPin,
  BedDouble,
  Bath,
  Car,
  Maximize2,
  Building2,
  Sparkles,
  TrendingDown,
  Phone,
  Mail,
  MessageCircle,
  ExternalLink,
  Calendar,
  Tag,
  Activity,
} from "lucide-react";

import { DashboardLayout } from "@/components/admin/DashboardLayout";
import { api } from "@/lib/api";
import {
  formatCurrency,
  formatArea,
  formatRelativeDate,
  getScoreColor,
  getPropertyTypeLabel,
  cn,
} from "@/lib/utils";

export default function PropertyDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;

  const { data: property, isLoading, isError } = useQuery({
    queryKey: ["property", id],
    queryFn: () => api.get(`/properties/${id}`).then((r) => r.data),
  });

  const { data: similar } = useQuery({
    queryKey: ["property-similar", id],
    queryFn: () =>
      api.get(`/properties/${id}/similar?limit=3`).then((r) => r.data),
    enabled: !!property,
  });

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-4 animate-pulse">
          <div className="h-8 w-48 bg-muted rounded" />
          <div className="h-96 bg-muted rounded-2xl" />
          <div className="grid grid-cols-3 gap-4">
            <div className="h-24 bg-muted rounded-xl" />
            <div className="h-24 bg-muted rounded-xl" />
            <div className="h-24 bg-muted rounded-xl" />
          </div>
        </div>
      </DashboardLayout>
    );
  }

  if (isError || !property) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Building2 className="h-12 w-12 text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold text-foreground">
            Propiedad no encontrada
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            La propiedad que buscás no existe o fue dada de baja.
          </p>
          <Link
            href="/properties"
            className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            <ArrowLeft className="h-4 w-4" /> Volver a propiedades
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  const images = property.images?.length
    ? property.images
    : property.main_image_url
    ? [{ url: property.main_image_url }]
    : [];

  const priceUYU =
    property.currency === "UYU"
      ? Number(property.price)
      : Number(property.price_usd) * 40;

  const isRent = property.operation === "alquiler";

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in pb-12">
        {/* Back */}
        <Link
          href="/properties"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Volver a propiedades
        </Link>

        {/* Galería */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div className="lg:col-span-2 relative aspect-[16/10] rounded-2xl overflow-hidden bg-muted">
            {images[0] ? (
              <Image
                src={images[0].url}
                alt={property.title}
                fill
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 66vw"
                unoptimized
              />
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                <Building2 className="h-12 w-12" />
              </div>
            )}
            <div className="absolute top-4 left-4 flex gap-2">
              <span
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-semibold backdrop-blur",
                  isRent
                    ? "bg-blue-500/90 text-white"
                    : "bg-emerald-500/90 text-white"
                )}
              >
                {isRent ? "Alquiler" : "Venta"}
              </span>
              {property.ai_premium && (
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-400/90 text-amber-950 flex items-center gap-1">
                  <Sparkles className="h-3 w-3" /> Premium
                </span>
              )}
              {property.ai_opportunity && (
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-500/90 text-white flex items-center gap-1">
                  <TrendingDown className="h-3 w-3" /> Oportunidad
                </span>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-1 gap-3">
            {images.slice(1, 3).map((img: any, i: number) => (
              <div
                key={i}
                className="relative aspect-[16/10] lg:aspect-auto lg:h-full rounded-xl overflow-hidden bg-muted"
              >
                <Image
                  src={img.url}
                  alt={`${property.title} ${i + 2}`}
                  fill
                  className="object-cover"
                  sizes="33vw"
                  unoptimized
                />
              </div>
            ))}
            {images.length <= 1 && (
              <div className="rounded-xl bg-muted flex items-center justify-center text-muted-foreground text-sm aspect-[16/10] lg:aspect-auto lg:h-full">
                Sin más imágenes
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Columna principal */}
          <div className="lg:col-span-2 space-y-6">
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <MapPin className="h-4 w-4" />
                {property.neighborhood}, {property.city}
              </div>
              <h1 className="text-2xl font-bold text-foreground">
                {property.title}
              </h1>
              <div className="flex items-baseline gap-3 mt-3">
                <span className="text-3xl font-bold text-foreground">
                  {formatCurrency(Number(property.price), property.currency)}
                  {isRent && (
                    <span className="text-base font-normal text-muted-foreground">
                      /mes
                    </span>
                  )}
                </span>
                {property.currency === "UYU" && (
                  <span className="text-sm text-muted-foreground">
                    ≈ {formatCurrency(Number(property.price_usd), "USD")}
                  </span>
                )}
              </div>
            </div>

            {/* Características */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Feature icon={<BedDouble />} label="Dormitorios" value={property.bedrooms ?? "—"} />
              <Feature icon={<Bath />} label="Baños" value={property.bathrooms ?? "—"} />
              <Feature icon={<Car />} label="Garajes" value={property.garages ?? "—"} />
              <Feature icon={<Maximize2 />} label="Superficie" value={formatArea(Number(property.area_total))} />
            </div>

            {/* Descripción */}
            {property.description && (
              <section>
                <h2 className="text-lg font-semibold text-foreground mb-2">
                  Descripción
                </h2>
                <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                  {property.description}
                </p>
              </section>
            )}

            {/* Análisis IA */}
            {(property.ai_summary || property.ai_tags?.length) && (
              <section className="rounded-2xl border bg-gradient-to-br from-brand-50 to-transparent p-5">
                <h2 className="text-lg font-semibold text-foreground mb-2 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-brand-500" /> Análisis IA
                </h2>
                {property.ai_summary && (
                  <p className="text-sm text-foreground/80 mb-3">
                    {property.ai_summary}
                  </p>
                )}
                {property.ai_tags?.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {property.ai_tags.map((tag: string) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/70 border text-xs text-foreground"
                      >
                        <Tag className="h-3 w-3 text-brand-500" />
                        {tag.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                )}
              </section>
            )}
          </div>

          {/* Sidebar derecha */}
          <div className="space-y-4">
            {/* Score IA */}
            {property.ai_score != null && (
              <div className="rounded-2xl border bg-card p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Score IA</span>
                  <span
                    className={cn(
                      "text-2xl font-bold",
                      getScoreColor(property.ai_score)
                    )}
                  >
                    {property.ai_score.toFixed(0)}
                  </span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-brand-500 rounded-full"
                    style={{ width: `${property.ai_score}%` }}
                  />
                </div>
              </div>
            )}

            {/* Datos */}
            <div className="rounded-2xl border bg-card p-5 space-y-3 text-sm">
              <Row label="Tipo" value={getPropertyTypeLabel(property.property_type)} />
              <Row label="Operación" value={isRent ? "Alquiler" : "Venta"} />
              {property.price_per_m2_usd && (
                <Row
                  label="Precio/m²"
                  value={formatCurrency(Number(property.price_per_m2_usd), "USD") + "/m²"}
                />
              )}
              <Row label="Fuente" value={property.source} />
              {property.agency_name && (
                <Row label="Inmobiliaria" value={property.agency_name} />
              )}
              <Row
                label="Publicado"
                value={formatRelativeDate(property.created_at)}
                icon={<Calendar className="h-3.5 w-3.5" />}
              />
            </div>

            {/* Contacto */}
            <div className="rounded-2xl border bg-card p-5 space-y-2">
              <h3 className="text-sm font-semibold text-foreground mb-1">
                Contacto
              </h3>
              {property.contact_whatsapp && (
                <a
                  href={`https://wa.me/${property.contact_whatsapp.replace(/\D/g, "")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-green-600 hover:underline"
                >
                  <MessageCircle className="h-4 w-4" /> WhatsApp
                </a>
              )}
              {property.contact_phone && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Phone className="h-4 w-4" /> {property.contact_phone}
                </div>
              )}
              {property.contact_email && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Mail className="h-4 w-4" /> {property.contact_email}
                </div>
              )}
              {property.url && (
                <a
                  href={property.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-brand-600 hover:underline pt-1"
                >
                  <ExternalLink className="h-4 w-4" /> Ver publicación original
                </a>
              )}
              {!property.contact_whatsapp &&
                !property.contact_phone &&
                !property.contact_email && (
                  <p className="text-xs text-muted-foreground">
                    Consultá en la publicación original.
                  </p>
                )}
            </div>
          </div>
        </div>

        {/* Similares */}
        {similar?.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-foreground mb-3 flex items-center gap-2">
              <Activity className="h-5 w-5 text-brand-500" /> Propiedades similares
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {similar.map((p: any) => (
                <Link
                  key={p.id}
                  href={`/properties/${p.id}`}
                  className="rounded-xl border bg-card p-4 hover:shadow-card-hover transition-shadow"
                >
                  <div className="text-xs text-muted-foreground mb-1">
                    {p.neighborhood}
                  </div>
                  <div className="font-semibold text-foreground text-sm line-clamp-1">
                    {p.title}
                  </div>
                  <div className="mt-2 font-bold text-foreground">
                    {formatCurrency(Number(p.price), p.currency)}
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </DashboardLayout>
  );
}

function Feature({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border bg-card p-3 flex flex-col items-center text-center">
      <span className="text-brand-500 mb-1 [&>svg]:h-5 [&>svg]:w-5">{icon}</span>
      <span className="text-base font-semibold text-foreground">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

function Row({
  label,
  value,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground flex items-center gap-1.5">
        {icon}
        {label}
      </span>
      <span className="font-medium text-foreground capitalize">{value}</span>
    </div>
  );
}
