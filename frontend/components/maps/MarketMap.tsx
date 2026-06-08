"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// Coordenadas de Punta del Este
const PDE_CENTER: [number, number] = [-54.9367, -34.9633];
const PDE_BOUNDS: [[number, number], [number, number]] = [
  [-55.2, -35.2],
  [-54.5, -34.7],
];

interface MapProperty {
  id: string;
  latitude: number;
  longitude: number;
  price_usd: number;
  property_type: string;
  operation: string;
  ai_premium: boolean;
  ai_opportunity: boolean;
  neighborhood: string;
}

export function MarketMap() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapboxToken] = useState(process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "");

  const { data: properties } = useQuery({
    queryKey: ["map-properties"],
    queryFn: () =>
      api
        .get("/properties/?page_size=100&status=active")
        .then((r) => r.data.items as MapProperty[]),
  });

  useEffect(() => {
    if (!mapboxToken || !mapContainer.current || mapRef.current) return;

    const initMap = async () => {
      try {
        const mapboxgl = (await import("mapbox-gl")).default;
        mapboxgl.accessToken = mapboxToken;

        const map = new mapboxgl.Map({
          container: mapContainer.current!,
          style: "mapbox://styles/mapbox/light-v11",
          center: PDE_CENTER,
          zoom: 11,
          maxBounds: PDE_BOUNDS,
        });

        map.on("load", () => {
          setMapLoaded(true);
          mapRef.current = map;
        });

        // Agregar controles
        map.addControl(new mapboxgl.NavigationControl(), "top-right");

        return () => map.remove();
      } catch (error) {
        console.error("Error inicializando Mapbox:", error);
      }
    };

    initMap();
  }, [mapboxToken]);

  // Agregar propiedades al mapa
  useEffect(() => {
    if (!mapRef.current || !mapLoaded || !properties) return;

    const map = mapRef.current;

    // Crear GeoJSON con las propiedades
    const geoJson = {
      type: "FeatureCollection" as const,
      features: properties
        .filter((p) => p.latitude && p.longitude)
        .map((p) => ({
          type: "Feature" as const,
          geometry: {
            type: "Point" as const,
            coordinates: [p.longitude, p.latitude],
          },
          properties: {
            id: p.id,
            price: p.price_usd,
            type: p.property_type,
            operation: p.operation,
            premium: p.ai_premium,
            opportunity: p.ai_opportunity,
            neighborhood: p.neighborhood,
          },
        })),
    };

    // Source de propiedades
    if (map.getSource("properties")) {
      (map.getSource("properties") as any).setData(geoJson);
    } else {
      map.addSource("properties", { type: "geojson", data: geoJson, cluster: true, clusterMaxZoom: 14 });

      // Capa de clusters
      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "properties",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": ["step", ["get", "point_count"], "#0ea5e9", 10, "#f59e0b", 50, "#8b5cf6"],
          "circle-radius": ["step", ["get", "point_count"], 20, 10, 30, 50, 40],
          "circle-opacity": 0.85,
        },
      });

      // Conteo de clusters
      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "properties",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
          "text-size": 12,
        },
        paint: { "text-color": "#fff" },
      });

      // Puntos individuales
      map.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "properties",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": [
            "case",
            ["==", ["get", "premium"], true], "#f59e0b",
            ["==", ["get", "opportunity"], true], "#10b981",
            "#0ea5e9",
          ],
          "circle-radius": 6,
          "circle-stroke-width": 2,
          "circle-stroke-color": "#fff",
        },
      });

      // Popup en click
      map.on("click", "unclustered-point", (e: any) => {
        const props = e.features[0].properties;
        const coords = e.features[0].geometry.coordinates;

        new (require("mapbox-gl")).default.Popup()
          .setLngLat(coords)
          .setHTML(`
            <div style="font-family: sans-serif; font-size: 13px; padding: 4px">
              <strong>${props.neighborhood || "Punta del Este"}</strong><br/>
              USD ${Number(props.price).toLocaleString()}<br/>
              <span style="color: #6b7280">${props.type}</span>
            </div>
          `)
          .addTo(map);
      });

      map.on("mouseenter", "unclustered-point", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "unclustered-point", () => {
        map.getCanvas().style.cursor = "";
      });
    }
  }, [mapLoaded, properties]);

  // Fallback si no hay token de Mapbox
  if (!mapboxToken) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-muted/30 text-center p-8">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <svg className="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        </div>
        <p className="font-medium text-sm">Mapa no disponible</p>
        <p className="text-xs text-muted-foreground mt-1">
          Configura NEXT_PUBLIC_MAPBOX_TOKEN para activar el mapa
        </p>
        {/* Mapa estático de placeholder */}
        <div className="mt-4 w-full max-w-sm h-32 rounded-lg overflow-hidden">
          <img
            src={`https://api.mapbox.com/styles/v1/mapbox/light-v11/static/-54.9367,-34.9633,11,0/400x200?access_token=pk.placeholder`}
            alt="Mapa Punta del Este"
            className="w-full h-full object-cover opacity-50"
            onError={(e) => e.currentTarget.style.display = 'none'}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Leyenda */}
      <div className="map-overlay p-3 text-xs">
        <p className="font-medium mb-2">Leyenda</p>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-400" />
            <span className="text-muted-foreground">Premium</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-muted-foreground">Oportunidad</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-brand-500" />
            <span className="text-muted-foreground">Estándar</span>
          </div>
        </div>
      </div>
    </div>
  );
}
