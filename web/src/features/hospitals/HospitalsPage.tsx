import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Hospital } from "@/api/client";

const VERSORGUNGSSTUFEN = ["Grund", "Regel", "Schwerpunkt", "Maximal"];

function DeficitBadge({ score }: { score: number }) {
  const cls =
    score >= 70 ? "bg-red-100 text-red-700" :
    score >= 40 ? "bg-yellow-100 text-yellow-700" :
    "bg-green-100 text-green-700";
  return <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${cls}`}>{score.toFixed(1)}</span>;
}

export function HospitalsPage() {
  const [search, setSearch] = useState("");
  const [versorgungsstufe, setVersorgungsstufe] = useState("");
  const [page, setPage] = useState(1);
  const [berichtsjahr] = useState(2022);

  const { data, isLoading } = useQuery({
    queryKey: ["hospitals", { search, versorgungsstufe, page, berichtsjahr }],
    queryFn: () =>
      api.hospitals.list({
        berichtsjahr,
        search: search || undefined,
        versorgungsstufe: versorgungsstufe || undefined,
        page,
        page_size: 50,
      }),
    placeholderData: (prev) => prev,
  });

  const totalPages = data ? Math.ceil(data.total / 50) : 1;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Krankenhäuser</h1>
        <p className="text-sm text-gray-500 mt-1">
          {data ? `${data.total.toLocaleString("de-DE")} Einrichtungen` : "Lade…"} · Berichtsjahr {berichtsjahr}
        </p>
      </div>

      <div className="flex gap-3 flex-wrap">
        <input
          type="search"
          placeholder="Name oder IK-Nummer suchen…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
        <select
          value={versorgungsstufe}
          onChange={(e) => { setVersorgungsstufe(e.target.value); setPage(1); }}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          <option value="">Alle Versorgungsstufen</option>
          {VERSORGUNGSSTUFEN.map((v) => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Ort</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Stufe</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600">Defizit</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600">SMR</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600">PpUGV %</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600">Betten</th>
              <th className="text-right px-4 py-2 font-medium text-gray-600">Konfidenz</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Lade…</td></tr>
            )}
            {!isLoading && data?.items.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Keine Einrichtungen gefunden.</td></tr>
            )}
            {data?.items.map((h: Hospital) => (
              <tr key={h.ik_nummer} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-2">
                  <span className="font-medium">{h.name ?? "–"}</span>
                  <span className="text-xs text-gray-400 ml-1">({h.ik_nummer})</span>
                </td>
                <td className="px-4 py-2 text-gray-600">{[h.plz, h.ort].filter(Boolean).join(" ")}</td>
                <td className="px-4 py-2">
                  {h.versorgungsstufe && (
                    <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{h.versorgungsstufe}</span>
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  {h.kpi ? <DeficitBadge score={h.kpi.def_index} /> : <span className="text-gray-300">–</span>}
                </td>
                <td className="px-4 py-2 text-right text-gray-600">{h.kpi?.mort_adj?.toFixed(2) ?? "–"}</td>
                <td className="px-4 py-2 text-right text-gray-600">{h.kpi?.ppugv_quote?.toFixed(1) ?? "–"}</td>
                <td className="px-4 py-2 text-right text-gray-600">{h.kpi?.betten?.toLocaleString("de-DE") ?? "–"}</td>
                <td className="px-4 py-2 text-right">
                  {h.kpi ? (
                    <span className={`text-xs ${h.kpi.konfidenz >= 0.8 ? "text-green-600" : h.kpi.konfidenz >= 0.5 ? "text-yellow-600" : "text-red-500"}`}>
                      {(h.kpi.konfidenz * 100).toFixed(0)}%
                    </span>
                  ) : "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-2 justify-end text-sm">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)}
            className="px-3 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">
            ‹ Zurück
          </button>
          <span className="text-gray-500">Seite {page} / {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}
            className="px-3 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">
            Weiter ›
          </button>
        </div>
      )}
    </div>
  );
}
