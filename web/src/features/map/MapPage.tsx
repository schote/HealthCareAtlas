export function MapPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Karte</h1>
        <p className="text-sm text-gray-500 mt-1">Geografische Verteilung der Versorgungsdefizite</p>
      </div>
      <div className="border rounded-lg p-12 text-center text-gray-400 min-h-[400px] flex flex-col items-center justify-center gap-2">
        <p className="text-4xl">🗺️</p>
        <p className="font-medium text-gray-500">Kartogramm (Phase 2)</p>
        <p className="text-sm max-w-sm">
          Das interaktive Tile-Kartogramm wird in Phase 2 mit echten BKG-Geometrien
          und OSRM-Routing implementiert.
        </p>
      </div>
    </div>
  );
}
