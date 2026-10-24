// Data layer: live FastAPI when VITE_API_URL is set, otherwise static JSON exported to /data.
import { useEffect, useState } from 'react'

export type Breakdown = { replication: number; design: number; markers: number; species: number; dose: number }

export type DrugSummary = {
  rank: number
  drug: string
  category: 'control_pos' | 'control_neg' | 'candidate'
  score: number
  confidence_label: 'high' | 'moderate' | 'low'
  n_pro: number
  n_anti: number
  n_claims: number
  n_conflicts: number
  pathways: string[]
  safety_flag: boolean
  breakdown: Breakdown
  top_design: string | null
  top_species: string | null
  trials: number
  why: string
}

export type Claim = {
  id: number
  paper_id: number
  stage: string
  direction: 'increase' | 'decrease' | 'no_effect' | 'mixed'
  species: string | null
  model_system: string | null
  brain_region: string | null
  markers: string | null
  pathways: string | null
  dose: string | null
  duration: string | null
  n: string | null
  study_design: string | null
  evidence_quote: string
  quote_verified: number
  confidence: number
  penalties: string | null
  pmid: string | null
  doi: string | null
  title: string
  year: number | null
  source_url: string | null
}

export type Conflict = {
  drug: string
  stage: string
  severity: 'strong' | 'weak'
  sides: Record<string, Claim[]>
}

export type DrugDetail = DrugSummary & {
  claims: Claim[]
  conflicts: Conflict[]
  trials: { nct_id: string; phase: string | null; status: string | null; condition: string | null; source_url: string }[]
  notes: { bbb_note: string | null; safety_note: string | null; source_url: string | null } | null
  disclaimer: string
}

export type GraphData = {
  nodes: { id: string; type: 'drug' | 'pathway' | 'stage' | 'disease'; label: string; score?: number; safety_flag?: boolean }[]
  links: { source: string; target: string; type: string; confidence: number; direction: string; n_claims: number; claim_ids: number[] }[]
}

export type Stats = {
  papers: number
  papers_fulltext: number
  papers_with_claims: number
  claims_verified: number
  drugs_scored: number
  drugs_total: number
  conflicts: number
  tinyfish: Record<string, { live: number; cached: number; errors: number }>
  weights: Record<string, number>
  penalties: Record<string, number>
  extractor_model: string
  validation: Validation | null
  extraction_eval: Record<string, { precision: number; recall: number; f1: number } | number> | null
  disclaimer: string
}

export type Validation = {
  controls: { drug: string; kind: 'positive' | 'negative'; expected: string; observed: string; ok: boolean; score: number; rank: number }[]
  recovered: number
  total: number
  quote_verified_fraction: number | null
  ablation: { label: string; positives_mean_rank: number; negatives_mean_rank: number; separation: number }[]
}

const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '')
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '')

async function getJson<T>(live: string, stat: string): Promise<T> {
  const url = API ? `${API}${live}` : `${BASE}/data/${stat}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchDrugs = () => getJson<DrugSummary[]>('/drugs', 'drugs.json')
export const fetchDrug = (name: string) =>
  getJson<DrugDetail>(`/drugs/${encodeURIComponent(name)}`, `drug/${name.replace(/ /g, '_')}.json`)
export const fetchGraph = () => getJson<GraphData>('/graph', 'graph.json')
export const fetchStats = () => getJson<Stats>('/stats', 'stats.json')

export type Async<T> = { data: T | null; error: string | null; loading: boolean }

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): Async<T> {
  const [state, setState] = useState<Async<T>>({ data: null, error: null, loading: true })
  useEffect(() => {
    let live = true
    setState({ data: null, error: null, loading: true })
    fn()
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((e: Error) => live && setState({ data: null, error: e.message, loading: false }))
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}
