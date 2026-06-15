const API_BASE = import.meta.env.VITE_API_URL ?? "";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${response.statusText} (${path})`);
  }
  return response.json() as Promise<T>;
}

// ─── Types (mirrors Pydantic schemas) ────────────────────────────────────────

export interface HospitalKPI {
  berichtsjahr: number;
  def_index: number;
  mort_adj: number | null;
  ppugv_quote: number | null;
  access_min: number | null;
  minq_quote: number | null;
  casemix_index: number | null;
  betten: number | null;
  konfidenz: number;
  datenstand: string;
}

export interface Hospital {
  ik_nummer: string;
  name: string | null;
  ort: string | null;
  plz: string | null;
  ags: string | null;
  versorgungsstufe: "Grund" | "Regel" | "Schwerpunkt" | "Maximal" | null;
  kpi: HospitalKPI | null;
}

export interface HospitalDetail extends Hospital {
  strasse: string | null;
  standort_id: string | null;
}

export interface HospitalList {
  total: number;
  items: Hospital[];
  page: number;
  page_size: number;
}

export interface Region {
  ags: string;
  name: string;
  ebene: string;
  parent_ags: string | null;
  einwohner: number | null;
  anteil_65plus: number | null;
  morbiditaet_idx: number | null;
}

export interface MetricDefinition {
  key: string;
  label: string;
  description: string;
  unit: string;
  weight: number;
  source: string;
}

export interface DeficitRankingItem {
  rang: number;
  entity_id: string;
  name: string | null;
  ebene: string;
  metric_key: string;
  score: number;
  berichtsjahr: number;
}

export interface DeficitRanking {
  total: number;
  berichtsjahr: number;
  items: DeficitRankingItem[];
}

// ─── API functions ────────────────────────────────────────────────────────────

export const api = {
  hospitals: {
    list: (params: {
      berichtsjahr?: number;
      page?: number;
      page_size?: number;
      search?: string;
      min_def_index?: number;
      max_def_index?: number;
      versorgungsstufe?: string;
    } = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) qs.set(k, String(v));
      });
      return apiFetch<HospitalList>(`/hospitals?${qs}`);
    },
    get: (ik: string, berichtsjahr?: number) => {
      const qs = berichtsjahr ? `?berichtsjahr=${berichtsjahr}` : "";
      return apiFetch<HospitalDetail>(`/hospitals/${encodeURIComponent(ik)}${qs}`);
    },
  },

  regions: {
    list: (ebene?: string) => {
      const qs = ebene ? `?ebene=${encodeURIComponent(ebene)}` : "";
      return apiFetch<Region[]>(`/regions${qs}`);
    },
    get: (ags: string) => apiFetch<Region & { children: Region[] }>(`/regions/${ags}`),
  },

  metrics: {
    list: () => apiFetch<MetricDefinition[]>("/metrics"),
  },

  deficit: {
    ranking: (params: {
      berichtsjahr?: number;
      ebene?: string;
      metric_key?: string;
      limit?: number;
      offset?: number;
    } = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) qs.set(k, String(v));
      });
      return apiFetch<DeficitRanking>(`/deficit/ranking?${qs}`);
    },
  },
};
