import { useState } from "react";
import { OverviewPage } from "./features/overview/OverviewPage";
import { HospitalsPage } from "./features/hospitals/HospitalsPage";
import { RegionalPage } from "./features/regional/RegionalPage";
import { AnalysisPage } from "./features/analysis/AnalysisPage";
import { MapPage } from "./features/map/MapPage";

type View = "overview" | "map" | "regional" | "hospitals" | "analysis";

const NAV: { id: View; label: string }[] = [
  { id: "overview", label: "Übersicht" },
  { id: "map", label: "Karte" },
  { id: "regional", label: "Regionalvergleich" },
  { id: "hospitals", label: "Krankenhäuser" },
  { id: "analysis", label: "Analyse" },
];

export default function App() {
  const [view, setView] = useState<View>("overview");

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-white sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-8">
          <span className="font-bold text-lg text-blue-700">Versorgungsatlas</span>
          <nav className="flex gap-1">
            {NAV.map((n) => (
              <button
                key={n.id}
                onClick={() => setView(n.id)}
                className={[
                  "px-3 py-1.5 rounded text-sm font-medium transition-colors",
                  view === n.id
                    ? "bg-blue-100 text-blue-800"
                    : "text-gray-600 hover:bg-gray-100",
                ].join(" ")}
              >
                {n.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {view === "overview" && <OverviewPage />}
        {view === "map" && <MapPage />}
        {view === "regional" && <RegionalPage />}
        {view === "hospitals" && <HospitalsPage />}
        {view === "analysis" && <AnalysisPage />}
      </main>
    </div>
  );
}
