"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

// Mock data para development — reemplazar con datos reales de la API
const MOCK_DATA = [
  { month: "Ago 23", "Punta del Este": 3200, "La Barra": 4100, "José Ignacio": 5200, "Cantegril": 2100 },
  { month: "Sep 23", "Punta del Este": 3150, "La Barra": 4050, "José Ignacio": 5100, "Cantegril": 2050 },
  { month: "Oct 23", "Punta del Este": 3300, "La Barra": 4300, "José Ignacio": 5500, "Cantegril": 2200 },
  { month: "Nov 23", "Punta del Este": 3400, "La Barra": 4400, "José Ignacio": 5700, "Cantegril": 2250 },
  { month: "Dic 23", "Punta del Este": 3600, "La Barra": 4800, "José Ignacio": 6200, "Cantegril": 2400 },
  { month: "Ene 24", "Punta del Este": 3800, "La Barra": 5100, "José Ignacio": 6800, "Cantegril": 2500 },
  { month: "Feb 24", "Punta del Este": 3750, "La Barra": 4950, "José Ignacio": 6600, "Cantegril": 2450 },
  { month: "Mar 24", "Punta del Este": 3500, "La Barra": 4600, "José Ignacio": 5900, "Cantegril": 2300 },
  { month: "Abr 24", "Punta del Este": 3400, "La Barra": 4400, "José Ignacio": 5600, "Cantegril": 2200 },
  { month: "May 24", "Punta del Este": 3450, "La Barra": 4450, "José Ignacio": 5700, "Cantegril": 2250 },
  { month: "Jun 24", "Punta del Este": 3500, "La Barra": 4500, "José Ignacio": 5800, "Cantegril": 2300 },
];

const ZONE_COLORS: Record<string, string> = {
  "Punta del Este": "#0ea5e9",
  "La Barra": "#f59e0b",
  "José Ignacio": "#8b5cf6",
  "Cantegril": "#10b981",
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-card border shadow-lg rounded-lg p-3">
      <p className="font-medium text-sm mb-2">{label}</p>
      {payload.map((entry: any) => (
        <div key={entry.name} className="flex items-center gap-2 text-xs">
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium">USD {entry.value.toLocaleString()}/m²</span>
        </div>
      ))}
    </div>
  );
};

export function PriceChart() {
  return (
    <div className="w-full h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={MOCK_DATA} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: "11px" }}
            iconType="circle"
            iconSize={8}
          />
          {Object.entries(ZONE_COLORS).map(([zone, color]) => (
            <Line
              key={zone}
              type="monotone"
              dataKey={zone}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
