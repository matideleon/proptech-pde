"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  MessagesSquare,
  RefreshCw,
  MapPin,
  BedDouble,
  Phone,
  ExternalLink,
  Home,
  Search,
  Clock,
} from "lucide-react";
import { DashboardLayout } from "@/components/admin/DashboardLayout";
import { groupPostsApi, GroupPost } from "@/lib/api";
import { cn } from "@/lib/utils";

type Kind = "all" | "oferta" | "demanda";

const PERIOD_LABEL: Record<string, string> = {
  anual: "Anual",
  invernal: "Invernal",
  temporada: "Temporada",
  diario: "Diario",
};

/** Nombre legible del portal a partir de la URL del link externo. */
function portalName(url: string): string {
  if (url.includes("marketplace/item")) return "Marketplace";
  if (url.includes("infocasas")) return "InfoCasas";
  if (url.includes("mercadolibre")) return "MercadoLibre";
  if (url.includes("gallito")) return "Gallito";
  if (url.includes("properati")) return "Properati";
  if (url.includes("zonaprop")) return "ZonaProp";
  return "Ver aviso";
}

export default function GroupPostsPage() {
  const [kind, setKind] = useState<Kind>("all");
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const filters = {
    page,
    page_size: 21,
    ...(kind !== "all" ? { kind } : {}),
  };

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["group-posts", filters],
    queryFn: () => groupPostsApi.list(filters).then((r) => r.data),
  });

  const trigger = useMutation({
    mutationFn: () => groupPostsApi.trigger(),
    onSuccess: () =>
      setTimeout(() => qc.invalidateQueries({ queryKey: ["group-posts"] }), 1500),
  });

  const tabs: { key: Kind; label: string }[] = [
    { key: "all", label: "Todas" },
    { key: "oferta", label: "Ofertas" },
    { key: "demanda", label: "Demandas" },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-4 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <MessagesSquare className="h-6 w-6 text-brand-500" />
              Grupos de Facebook
            </h1>
            <p className="text-sm text-muted-foreground">
              Alquileres ofrecidos y solicitados, detectados en tus grupos ·{" "}
              {isLoading ? "…" : `${data?.total ?? 0} posts`}
            </p>
          </div>
          <button
            onClick={() => trigger.mutate()}
            disabled={trigger.isPending}
            className="flex items-center gap-2 bg-brand-500 text-white rounded-lg px-3 py-2 text-sm hover:bg-brand-600 transition-colors disabled:opacity-60"
          >
            <RefreshCw className={cn("h-4 w-4", trigger.isPending && "animate-spin")} />
            {trigger.isPending ? "Revisando…" : "Revisar grupos ahora"}
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-card border rounded-lg p-1 w-fit">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => {
                setKind(t.key);
                setPage(1);
              }}
              className={cn(
                "px-4 py-1.5 rounded-md text-sm transition-colors",
                kind === t.key
                  ? "bg-brand-500 text-white"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Lista */}
        {isLoading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-44 rounded-xl border skeleton" />
            ))}
          </div>
        ) : data?.items?.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <Search className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p>No hay posts todavía. Probá “Revisar grupos ahora”.</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data?.items?.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        )}

        {/* Paginación numerada */}
        {data && data.pages > 1 && (
          <Pagination current={page} total={data.pages} onChange={setPage} />
        )}
        {isFetching && !isLoading && (
          <p className="text-center text-xs text-muted-foreground">Actualizando…</p>
        )}
      </div>
    </DashboardLayout>
  );
}

function PostCard({ post }: { post: GroupPost }) {
  const isOffer = post.kind === "oferta";
  const refDate = post.posted_at ?? post.created_at;
  const hoursAgo = (Date.now() - new Date(refDate).getTime()) / 3_600_000;
  const timeLabel =
    hoursAgo < 1
      ? "hace menos de 1h"
      : hoursAgo < 24
      ? `hace ${Math.floor(hoursAgo)}h`
      : hoursAgo < 48
      ? "hace 1 día"
      : `hace ${Math.floor(hoursAgo / 24)} días`;
  const timeBadgeClass =
    hoursAgo < 24
      ? "bg-amber-400 text-amber-900"
      : "bg-slate-500/80 text-slate-100";

  return (
    <div className="rounded-xl border bg-card p-4 flex flex-col gap-3 shadow-card">
      <div className="flex items-center justify-between">
        <span
          className={cn(
            "text-xs font-semibold px-2 py-0.5 rounded-full",
            isOffer
              ? "bg-emerald-100 text-emerald-700"
              : "bg-amber-100 text-amber-700"
          )}
        >
          {isOffer ? "🏠 Ofrece" : "🔍 Busca"}
        </span>
        <span className={cn("flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full", timeBadgeClass)}>
          <Clock className="h-2.5 w-2.5" />
          {timeLabel}
        </span>
      </div>

      {post.permalink ? (
        <a
          href={post.permalink}
          target="_blank"
          rel="noreferrer"
          title="Ver publicación en Facebook"
          className="text-sm leading-snug line-clamp-4 hover:text-brand-600 transition-colors"
        >
          {post.text}
        </a>
      ) : (
        <p className="text-sm leading-snug line-clamp-4">{post.text}</p>
      )}

      {post.external_links && post.external_links.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {post.external_links.map((url) => (
            <a
              key={url}
              href={url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md bg-brand-50 text-brand-600 border border-brand-200 hover:bg-brand-100 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              {portalName(url)}
            </a>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2 text-xs">
        {post.neighborhood && (
          <Chip icon={<MapPin className="h-3 w-3" />}>{post.neighborhood}</Chip>
        )}
        {post.price != null && (
          <Chip>
            {post.currency === "UYU" ? "$U" : "USD"} {Number(post.price).toLocaleString("es-UY")}
          </Chip>
        )}
        {post.bedrooms != null && (
          <Chip icon={<BedDouble className="h-3 w-3" />}>{post.bedrooms} dorm</Chip>
        )}
        {post.property_type && (
          <Chip icon={<Home className="h-3 w-3" />}>{post.property_type}</Chip>
        )}
        {post.period && <Chip>{PERIOD_LABEL[post.period] ?? post.period}</Chip>}
      </div>

      <div className="flex items-center justify-between mt-auto pt-1 border-t">
        <span className="text-xs text-muted-foreground truncate max-w-[55%]">
          {post.author_name || post.group_name || "Grupo FB"}
        </span>
        <div className="flex items-center gap-3">
          {post.contact_phone && (
            <a
              href={`https://wa.me/${post.contact_phone.replace(/\D/g, "")}`}
              target="_blank"
              rel="noreferrer"
              className="text-xs flex items-center gap-1 text-emerald-600 hover:underline"
            >
              <Phone className="h-3 w-3" /> WhatsApp
            </a>
          )}
          {post.permalink && (
            <a
              href={post.permalink}
              target="_blank"
              rel="noreferrer"
              title="Ver publicación en Facebook"
              className="text-xs flex items-center gap-1 text-brand-500 hover:underline"
            >
              <ExternalLink className="h-3 w-3" /> Ver post
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function Chip({ icon, children }: { icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 bg-muted rounded-md px-2 py-0.5">
      {icon}
      {children}
    </span>
  );
}

function Pagination({ current, total, onChange }: { current: number; total: number; onChange: (p: number) => void }) {
  const pages: (number | "…")[] = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) pages.push("…");
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i);
    if (current < total - 2) pages.push("…");
    pages.push(total);
  }

  return (
    <div className="flex items-center justify-center gap-1 pt-2 flex-wrap">
      <button
        disabled={current <= 1}
        onClick={() => onChange(current - 1)}
        className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-muted"
      >
        ‹
      </button>
      {pages.map((p, i) =>
        p === "…" ? (
          <span key={`ellipsis-${i}`} className="px-2 text-muted-foreground select-none">…</span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={cn(
              "min-w-[2rem] px-2 py-1.5 rounded-lg border text-sm transition-colors",
              p === current
                ? "bg-brand-500 text-white border-brand-500"
                : "hover:bg-muted"
            )}
          >
            {p}
          </button>
        )
      )}
      <button
        disabled={current >= total}
        onClick={() => onChange(current + 1)}
        className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-muted"
      >
        ›
      </button>
    </div>
  );
}
