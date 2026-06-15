import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api } from "@/api/client";

function colorForScore(score: number) {
  if (score >= 70) return "#ef4444";
  if (score >= 40) return "#f59e0b";
  return "#22c55e";
}

export function RegionalPage() {
  const { data: ranking, isLoading } = useQuery({
    queryKey: ["deficit-ranking-regional", 2022],
    queryFn: () => api.deficit.ranking({ berichtsjahr: 2022, limit: 16 }),
  });

  const chartData = ranking?.items.map((item) => ({
    name: (item.name ?? item.entity_id).substring(0, 25),
    score: item.score,
  })) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Regionalvergleich</h1>
        <p className="text-sm text-gray-500 mt-1">Defizit-Ranking nach Einrichtungen · Berichtsjahr 2022</p>
      </div>

      {isLoading ? (
        <p className="text-gray-400">Lade Daten…</p>
      ) : chartData.length === 0 ? (
        <div className="border rounded-lg p-12 text-center text-gray-400">
          Noch keine Daten — Pipeline muss zuerst ausgeführt werden.
        </div>
      ) : (
        <div className="border rounded-lg p-6">
          <h2 className="text-sm font-medium text-gray-600 mb-4">Defizit-Index nach Einrichtung</h2>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 160, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={160} />
              <Tooltip formatter={(v: number) => [`${v.toFixed(1)}`, "Defizit-Index"]} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={colorForScore(entry.score)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
