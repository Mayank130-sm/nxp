import { motion } from 'framer-motion'
import { ArrowUpRight, Search, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchDrugs, fetchStats, useAsync, type DrugSummary } from '../api'
import {
  Badge, ConfidenceBadge, ConflictBadge, CountUp, Disclaimer, Empty, ErrorBox, EvidenceChip, Reveal, SafetyBadge,
  ScoreRing, Skeleton, pretty, useDebounced,
} from '../ui'

type Filter = 'all' | 'pro' | 'safety' | 'conflict'
type Sort = 'score' | 'evidence' | 'name'

function Tile({ label, value, delay }: { label: string; value: number | undefined; delay: number }) {
  return (
    <Reveal delay={delay}>
      <div className="card px-5 py-4">
        <p className="caps">{label}</p>
        <p className="mt-1 font-serif text-4xl">{value === undefined ? <Skeleton className="h-10 w-20" /> : <CountUp value={value} />}</p>
      </div>
    </Reveal>
  )
}

function DrugCard({ d, i }: { d: DrugSummary; i: number }) {
  const scored = d.n_claims > 0
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: Math.min(i, 12) * 0.03 }} whileHover={{ y: -3 }}>
      <Link to={`/drug/${encodeURIComponent(d.drug)}`} className="card group block h-full p-5 transition-shadow hover:shadow-glow" aria-label={`${d.drug}, score ${d.score.toFixed(0)}`}>
        <div className="flex items-start gap-4">
          <ScoreRing score={d.score} />
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <h3 className="truncate text-xl capitalize">{d.drug}</h3>
              <ArrowUpRight size={16} className="mt-1.5 shrink-0 text-muted transition-colors group-hover:text-teal" aria-hidden />
            </div>
            <p className="caps mt-0.5">#{d.rank} · {d.category === 'candidate' ? 'candidate' : d.category === 'control_pos' ? 'positive control' : 'negative control'}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {scored ? <ConfidenceBadge label={d.confidence_label} /> : <Badge>no verified evidence</Badge>}
          {scored && <EvidenceChip n={d.n_claims} />}
          {d.n_conflicts > 0 && <ConflictBadge n={d.n_conflicts} />}
          {d.safety_flag && <SafetyBadge />}
        </div>
        <p className="mt-3 line-clamp-3 text-sm text-muted">{d.why}</p>
        {scored && (d.top_design || d.top_species) && (
          <p className="caps mt-3 normal-case tracking-normal">Best evidence: {pretty(d.top_design)} · {pretty(d.top_species)}</p>
        )}
      </Link>
    </motion.div>
  )
}

export default function Home() {
  const drugs = useAsync(fetchDrugs, [])
  const stats = useAsync(fetchStats, [])
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [sort, setSort] = useState<Sort>('score')
  const [design, setDesign] = useState('')
  const [species, setSpecies] = useState('')
  const [showAll, setShowAll] = useState(false)
  const dq = useDebounced(q)

  const options = useMemo(() => {
    const list = drugs.data ?? []
    const uniq = (f: (d: DrugSummary) => string | null) => [...new Set(list.map(f).filter(Boolean) as string[])].sort()
    return { designs: uniq((d) => d.top_design), species: uniq((d) => d.top_species) }
  }, [drugs.data])

  const shown = useMemo(() => {
    let list = drugs.data ?? []
    if (!showAll) list = list.filter((d) => d.n_claims > 0)
    if (dq) list = list.filter((d) => d.drug.toLowerCase().includes(dq.toLowerCase()))
    if (filter === 'pro') list = list.filter((d) => d.n_pro > 0 && !d.safety_flag)
    if (filter === 'safety') list = list.filter((d) => d.safety_flag)
    if (filter === 'conflict') list = list.filter((d) => d.n_conflicts > 0)
    if (design) list = list.filter((d) => d.top_design === design)
    if (species) list = list.filter((d) => d.top_species === species)
    return [...list].sort((a, b) =>
      sort === 'name' ? a.drug.localeCompare(b.drug) : sort === 'evidence' ? b.n_claims - a.n_claims : b.score - a.score)
  }, [drugs.data, dq, filter, sort, design, species, showAll])

  const chip = (k: Filter, label: string) => (
    <button key={k} onClick={() => setFilter(k)} aria-pressed={filter === k}
      className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${filter === k ? 'border-violet bg-violet/25 text-text' : 'border-white/10 text-muted hover:text-text'}`}>
      {label}
    </button>
  )
  const select = (value: string, set: (v: string) => void, label: string, opts: string[]) => (
    <select value={value} onChange={(e) => set(e.target.value)} aria-label={label}
      className="rounded-full border border-white/10 bg-surface px-3 py-1.5 text-sm text-muted focus:text-text">
      <option value="">{label}</option>
      {opts.map((o) => <option key={o} value={o}>{pretty(o)}</option>)}
    </select>
  )

  return (
    <main>
      <section className="noise relative overflow-hidden border-b border-white/[0.06]">
        <div className="hero-grid absolute inset-0" aria-hidden />
        <div className="absolute -top-40 left-1/2 h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-violet/25 blur-[120px]" aria-hidden />
        <div className="relative mx-auto max-w-6xl px-4 pb-14 pt-16 sm:px-6 sm:pt-24">
          <Reveal>
            <p className="caps text-teal">Neurogenesis · Alzheimer's disease · Drug repurposing</p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.1] sm:text-6xl">
              Which approved drugs deserve a lab test for <em className="text-teal">neurogenesis</em>?
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-muted">
              NeuroRx turns scattered, contradictory literature into a graph where every drug claim is linked to a paper, graded for
              confidence and flagged when contradicted.
            </p>
          </Reveal>
          <div className="mt-8 grid max-w-2xl grid-cols-3 gap-3">
            <Tile label="Papers processed" value={stats.data?.papers} delay={0.1} />
            <Tile label="Verified claims" value={stats.data?.claims_verified} delay={0.18} />
            <Tile label="Drugs scored" value={stats.data?.drugs_scored} delay={0.26} />
          </div>
          <Reveal delay={0.3} className="mt-8 max-w-xl">
            <label className="relative block">
              <span className="sr-only">Search drugs</span>
              <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a drug, e.g. metformin"
                className="w-full rounded-2xl border border-white/10 bg-surface/80 py-3.5 pl-11 pr-4 text-base shadow-card outline-none backdrop-blur placeholder:text-muted focus:border-violet" />
            </label>
          </Reveal>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <SlidersHorizontal size={16} className="mr-1 text-muted" aria-hidden />
          {chip('all', 'All')}{chip('pro', 'Pro-neurogenic')}{chip('safety', 'Safety flags')}{chip('conflict', 'Conflicted')}
          <span className="mx-1 hidden h-5 w-px bg-white/10 sm:block" aria-hidden />
          {select(design, setDesign, 'Any design', options.designs)}
          {select(species, setSpecies, 'Any species', options.species)}
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort"
            className="ml-auto rounded-full border border-white/10 bg-surface px-3 py-1.5 text-sm text-muted focus:text-text">
            <option value="score">Sort: score</option><option value="evidence">Sort: evidence</option><option value="name">Sort: name</option>
          </select>
          <label className="flex items-center gap-2 text-sm text-muted">
            <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} className="accent-violet" />
            Include unscored
          </label>
        </div>

        {drugs.error && <ErrorBox message={drugs.error} />}
        {drugs.loading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-52" />)}</div>
        )}
        {drugs.data && shown.length === 0 && <Empty title="No drugs match these filters" hint="Clear a filter or include unscored drugs." />}
        {drugs.data && shown.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{shown.map((d, i) => <DrugCard key={d.drug} d={d} i={i} />)}</div>
        )}
        <div className="mt-8"><Disclaimer /></div>
      </section>
    </main>
  )
}
