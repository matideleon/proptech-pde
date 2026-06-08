"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";

// Datos de ejemplo — reemplazar con datos reales
const MOCK_ZONES = [
  { zone: "José Ignacio", price_m2: 5800, count: 45 },
  { zone: "La Barra", price_m2: 4600, count: 128 },
  { zone: "Manantiales", price_m2: 4200, count: 67 },
  { zone: "Punta Ballena", price_m2: 3900, count: 89 },
  { zone: "San Rafael", price_m2: 3600, count: 52 },
  { zone: "PDE Centro", price_m2: 3400, count: 215 },
  { zone: "Cantegril", price_m2: 2800, count: 134 },
  { zone: "Pinares", price_m2: 2400, count: 98 },
  { zone: "Beverly Hills", price_m2: 2200, count: 76 },
  { zone: "Maldonado", price_m2: 1600, count: 312 },
];

function getBarColor(price: number): string {
  if (price >= 5000) return "#7c3aed"; // Premium extremo
  if (price >= 4000) return "#f59e0b"; // Premium
  if (price >= 3000) return "#0ea5e9"; // Alto
  if (price >= 2000) return "#10b981"; // Medio
  return "#6b7280";                    // Estándar
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  return (
    <div className="bg-card border shadow-lg rounded-lg p-3 text-xs">
      <p className="font-medium mb-1">{data.zone}</p>
      <p className="text-muted-foreground">
        Precio/m²: <span className="text-foreground font-medium">USD {data.price_m2.toLocaleString()}</span>
      </p>
      <p className="text-muted-foreground">
        Propiedades: <span className="text-foreground font-medium">{data.count}</span>
      </p>
    </div>
  );
};

interface HeatmapZonesProps {
  data?: Record<string, number>;
}

export function HeatmapZones({ data }: HeatmapZonesProps) {
  return (
    <div className="w-full h-48">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={MOCK_ZONES}
          layout="vertical"
          margin={{ top: 0, right: 30, bottom: 0, left: 70 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} className="stroke-border" />
          <XAxis
            type="number"
            tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          />
          <YAxis
            type="category"
            dataKey="zone"
            tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
            width={65}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="price_m2" radius={[0, 4, 4, 0]}>
            {MOCK_ZONES.map((entry, index) => (
              <Cell key={index} fill={getBarColor(entry.price_m2)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
