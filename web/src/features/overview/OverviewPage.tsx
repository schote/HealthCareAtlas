import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

function KpiCard({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <div className={`rounded-lg border p-4 ${color}`}>
      <p className="text-sm text-gray-600">{label}</p>
      <p className="text-2xl font-bold mt-1">{value} <span className="text-sm font-normal text-gray-500">{unit}</span></p>
    </div>
  );
}

export function OverviewPage() {
  const { data: ranking, isLoading } = useQuery({
    queryKey: ["deficit-ranking", 2022],
    queryFn: () => api.deficit.ranking({ berichtsjahr: 2022, limit: 10 }),
  });

  const { data: metrics } = useQuery({
    queryKey: ["metrics"],
    queryFn: () => api.metrics.list(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Nationale Übersicht</h1>
        <p className="text-gray-500 text-sm mt-1">Versorgungsqualität deutscher Krankenhäuser</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Berichtsjahr" value="2022" unit="" color="bg-blue-50 border-blue-200" />
        <KpiCard label="Krankenhäuser" value={String(ranking?.total ?? "–")} unit="gesamt" color="bg-green-50 border-green-200" />
        <KpiCard label="Metrik-Dimensionen" value={String(metrics?.length ?? "–")} unit="Indikatoren" color="bg-purple-50 border-purple-200" />
        <KpiCard label="Datenbasis" value="QB + §21 + PpUGV" unit="" color="bg-orange-50 border-orange-200" />
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">Top 10 Defizit-Einrichtungen (2022)</h2>
        {isLoading ? (
          <p className="text-gray-400">Lade Daten…</p>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Rang</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Einrichtung</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-600">Defizit-Index</th>
                </tr>
              </thead>
              <tbody>
                {ranking?.items.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-gray-400">
                      Noch keine Daten — Pipeline muss zuerst ausgeführt werden.
                    </td>
                  </tr>
                )}
                {ranking?.items.map((item) => (
                  <tr key={item.entity_id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-500">{item.rang}</td>
                    <td className="px-4 py-2 font-medium">{item.name ?? item.entity_id}</td>
                    <td className="px-4 py-2 text-right">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${
                        item.score >= 70 ? "bg-red-100 text-red-700" :
                        item.score >= 40 ? "bg-yellow-100 text-yellow-700" :
                        "bg-green-100 text-green-700"
                      }`}>
                        {item.score.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
