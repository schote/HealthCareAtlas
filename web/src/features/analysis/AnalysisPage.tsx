import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { api } from "@/api/client";

const AXIS_OPTIONS = [
  { key: "def_index", label: "Defizit-Index" },
  { key: "mort_adj", label: "Adjustierte Mortalität (SMR)" },
  { key: "ppugv_quote", label: "PpUGV-Konformität %" },
  { key: "access_min", label: "Erreichbarkeit (min)" },
  { key: "minq_quote", label: "Mindestmengen-Quote %" },
];

function colorFromDeficit(def: number) {
  const r = Math.round((def / 100) * 220);
  const g = Math.round(((100 - def) / 100) * 160);
  return `rgb(${r},${g},60)`;
}

export function AnalysisPage() {
  const [xAxis, setXAxis] = useState("access_min");
  const [yAxis, setYAxis] = useState("mort_adj");

  const { data, isLoading } = useQuery({
    queryKey: ["hospitals-analysis", 2022],
    queryFn: () => api.hospitals.list({ berichtsjahr: 2022, page_size: 500 }),
  });

  const points = (data?.items ?? [])
    .filter((h) => h.kpi != null)
    .map((h) => ({
      x: (h.kpi as unknown as Record<string, number | null>)[xAxis] ?? 0,
      y: (h.kpi as unknown as Record<string, number | null>)[yAxis] ?? 0,
      def: h.kpi!.def_index,
      name: h.name ?? h.ik_nummer,
      betten: h.kpi!.betten ?? 100,
    }));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analyse</h1>
        <p className="text-sm text-gray-500 mt-1">Streudiagramm aller Einrichtungen · Farbe = Defizit-Index</p>
      </div>

      <div className="flex gap-4 flex-wrap">
        <label className="flex items-center gap-2 text-sm">
          X-Achse:
          <select value={xAxis} onChange={(e) => setXAxis(e.target.value)}
            className="border rounded px-2 py-1 text-sm">
            {AXIS_OPTIONS.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          Y-Achse:
          <select value={yAxis} onChange={(e) => setYAxis(e.target.value)}
            className="border rounded px-2 py-1 text-sm">
            {AXIS_OPTIONS.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
          </select>
        </label>
      </div>

      <div className="border rounded-lg p-6">
        {isLoading ? (
          <p className="text-gray-400 text-center py-20">Lade Daten…</p>
        ) : points.length === 0 ? (
          <p className="text-gray-400 text-center py-20">Keine Daten — Pipeline muss zuerst ausgeführt werden.</p>
        ) : (
          <ResponsiveContainer width="100%" height={500}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="x" name={AXIS_OPTIONS.find((o) => o.key === xAxis)?.label} />
              <YAxis dataKey="y" name={AXIS_OPTIONS.find((o) => o.key === yAxis)?.label} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-white border rounded shadow-lg p-3 text-xs">
                      <p className="font-bold">{d.name}</p>
                      <p>Defizit: {d.def.toFixed(1)}</p>
                      <p>X ({xAxis}): {d.x?.toFixed(2)}</p>
                      <p>Y ({yAxis}): {d.y?.toFixed(2)}</p>
                    </div>
                  );
                }}
              />
              <Scatter data={points}>
                {points.map((p, i) => (
                  <Cell key={i} fill={colorFromDeficit(p.def)} fillOpacity={0.7} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
