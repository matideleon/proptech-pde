"use client";

import { useEffect, useRef, useState } from "react";
import { Property } from "@/types/property";

interface MarketMapProps {
  properties: Property[];
  mode: "heatmap" | "clusters";
}

export function MarketMap({ properties, mode }: MarketMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const initMap = async () => {
      try {
        const maplibregl = (await import("maplibre-gl")).default;

        const map = new maplibregl.Map({
          container: mapContainer.current!,
          style: {
            version: 8,
            sources: {
              osm: {
                type: "raster",
                tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                tileSize: 256,
                attribution: "© OpenStreetMap contributors",
              },
            },
            layers: [
              {
                id: "osm",
                type: "raster",
                source: "osm",
              },
            ],
          },
          center: [-54.95, -34.9],
          zoom: 12,
        });

        mapRef.current = map;

        map.addControl(new maplibregl.NavigationControl(), "top-right");

        map.on("load", () => {
          setMapLoaded(true);
        });
      } catch (err) {
        console.error("Error inicializando mapa:", err);
        setError("Error al cargar el mapa");
      }
    };

    initMap();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;

    const map = mapRef.current;
    const geojsonData = {
      type: "FeatureCollection" as const,
      features: properties
        .filter((p) => p.latitude && p.longitude)
        .map((p) => ({
          type: "Feature" as const,
          geometry: {
            type: "Point" as const,
            coordinates: [p.longitude!, p.latitude!],
          },
          properties: {
            price: p.price || 0,
            id: p.id,
            title: p.title,
          },
        })),
    };

    // Remove existing layers/sources
    ["heatmap-layer", "clusters", "cluster-count", "unclustered-point"].forEach((id) => {
      if (map.getLayer(id)) map.removeLayer(id);
    });
    ["properties-heat", "properties-cluster"].forEach((id) => {
      if (map.getSource(id)) map.removeSource(id);
    });

    if (mode === "heatmap") {
      map.addSource("properties-heat", { type: "geojson", data: geojsonData });
      map.addLayer({
        id: "heatmap-layer",
        type: "heatmap",
        source: "properties-heat",
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "price"], 0, 0, 1000000, 1],
          "heatmap-intensity": 1,
          "heatmap-color": [
            "interpolate", ["linear"], ["heatmap-density"],
            0, "rgba(33,102,172,0)",
            0.2, "rgb(103,169,207)",
            0.4, "rgb(209,229,240)",
            0.6, "rgb(253,219,199)",
            0.8, "rgb(239,138,98)",
            1, "rgb(178,24,43)",
          ],
          "heatmap-radius": 20,
          "heatmap-opacity": 0.8,
        },
      });
    } else {
      map.addSource("properties-cluster", {
        type: "geojson",
        data: geojsonData,
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      });
      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "properties-cluster",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": ["step", ["get", "point_count"], "#51bbd6", 10, "#f1f075", 30, "#f28cb1"],
          "circle-radius": ["step", ["get", "point_count"], 20, 10, 30, 30, 40],
        },
      });
      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "properties-cluster",
        filter: ["has", "point_count"],
        layout: { "text-field": "{point_count_abbreviated}", "text-size": 12 },
      });
      map.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "properties-cluster",
        filter: ["!", ["has", "point_count"]],
        paint: { "circle-color": "#11b4da", "circle-radius": 6, "circle-stroke-width": 1, "circle-stroke-color": "#fff" },
      });
    }
  }, [mapLoaded, properties, mode]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <p>{error}</p>
      </div>
    );
  }

  return <div ref={mapContainer} className="w-full h-full rounded-lg" />;
}
