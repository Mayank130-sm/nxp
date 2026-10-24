import { motion } from 'framer-motion'
import { ArrowRight, ArrowUpRight, BadgeCheck, Check, FileSearch, FlaskConical, Gauge, GitBranch, Globe, Scale, ShieldAlert, Sparkles, SplitSquareHorizontal } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DrugSummary, Stats } from './api'
import { Badge, ConfidenceBadge, CountUp, Skeleton, scoreColor } from './ui'

const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

const STEPS = [
  { icon: Globe, label: 'TinyFish Search', note: 'ranked open-access URLs' },
  { icon: FileSearch, label: 'TinyFish Fetch', note: 'Methods and Results as Markdown' },
  { icon: Sparkles, label: 'Extract claims', note: 'two gates, strict JSON schema' },
  { icon: BadgeCheck, label: 'Verify quote', note: 'exact substring or discarded' },
  { icon: Gauge, label: 'Grade 0-100', note: 'replication, design, markers' },
  { icon: Scale, label: 'Rank with a reason', note: 'conflicts and safety flags' },
]

function PipelineVisual() {
  const [active, setActive] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setActive((a) => (a + 1) % (STEPS.length + 1)), 1300)
    return () => window.clearInterval(id)
  }, [])
  return (
    <div className="card relative overflow-hidden p-5 shadow-glow" aria-label="Animated overview of the evidence pipeline">
      <div className="flex items-center justify-between">
        <p className="caps">Evidence pipeline</p>
        <span className="flex items-center gap-1.5 text-xs text-teal">
          <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal/70" /><span className="relative h-2 w-2 rounded-full bg-teal" /></span>
          running
        </span>
      </div>
      <ol className="mt-4 space-y-2">
        {STEPS.map((s, i) => {
          const done = i < active
          const on = i === active
          return (
            <li key={s.label} className={`relative flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors duration-500 ${on ? 'border-teal/50 bg-teal/10' : done ? 'border-white/10 bg-white/[0.03]' : 'border-white/[0.06]'}`}>
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${on ? 'bg-teal text-ink' : done ? 'bg-violet/25 text-[#b6adf5]' : 'bg-white/5 text-muted'}`}>
                {done ? <Check size={16} aria-hidden /> : <s.icon size={16} aria-hidden />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{s.label}</span>
                <span className="block truncate text-xs text-muted">{s.note}</span>
              </span>
              {on && <motion.span layoutId="scan" className="absolute inset-x-3 bottom-0 h-px bg-gradient-to-r from-transparent via-teal to-transparent" />}
              <span className="tnum text-xs text-muted">{done ? 'done' : on ? 'now' : 'queued'}</span>
            </li>
          )
        })}
      </ol>
      <motion.div key={active} initial={{ opacity: 0, y: 8 }} animate={{ opacity: active >= 4 ? 1 : 0, y: 0 }} className="mt-4 rounded-xl border border-white/10 bg-ink/60 p-3">
        <p className="text-xs text-muted">A claim is kept only if its quote appears word for word in the paper. Otherwise it is discarded.</p>
        <div className="mt-2 flex items-center gap-2"><Badge tone="teal" icon={<Check size={12} aria-hidden />}>quote verified</Badge><span className="text-xs text-muted">illustration of the rule</span></div>
      </motion.div>
    </div>
  )
}

export function Hero({ stats, onSearchFocus }: { stats: Stats | null; onSearchFocus: () => void }) {
  const tile = (label: string, v: number | undefined) => (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
      <p className="caps">{label}</p>
      <p className="mt-1 font-serif text-3xl">{v === undefined ? <Skeleton className="h-9 w-16" /> : <CountUp value={v} />}</p>
    </div>
  )
  return (
    <section className="noise relative overflow-hidden border-b border-white/[0.06]">
      <div className="hero-grid absolute inset-0" aria-hidden />
      <div className="absolute -top-40 left-1/4 h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-violet/30 blur-[130px]" aria-hidden />
      <div className="absolute -right-24 top-24 h-[320px] w-[420px] rounded-full bg-teal/15 blur-[120px]" aria-hidden />
      <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-14 sm:px-6 sm:pt-20 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-teal" /> Neurogenesis · Alzheimer's disease · Drug repurposing
          </motion.p>
          <motion.h1 initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="mt-5 text-4xl font-semibold leading-[1.05] sm:text-6xl">
            Which approved drugs deserve a lab test for <em className="text-teal">neurogenesis</em>?
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }} className="mt-5 max-w-xl text-lg text-muted">
            NeuroRx reads the literature with an agent pipeline, keeps only claims it can quote, grades each one, flags contradictions, and
            ranks drugs with a plain-language reason.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24 }} className="mt-7 flex flex-wrap gap-3">
            <button onClick={() => { scrollTo('ranking'); onSearchFocus() }} className="inline-flex items-center gap-2 rounded-xl bg-teal px-5 py-3 text-sm font-semibold text-ink transition-transform hover:-translate-y-0.5">
              Explore the ranking <ArrowRight size={16} aria-hidden />
            </button>
            <Link to="/graph" className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/[0.04] px-5 py-3 text-sm font-medium transition-colors hover:bg-white/10">
              <GitBranch size={16} aria-hidden /> Open the evidence graph
            </Link>
          </motion.div>
          <div className="mt-9 grid max-w-xl grid-cols-3 gap-3">
            {tile('Papers processed', stats?.papers)}
            {tile('Verified claims', stats?.claims_verified)}
            {tile('Drugs scored', stats?.drugs_scored)}
          </div>
        </div>
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}>
          <PipelineVisual />
        </motion.div>
      </div>
    </section>
  )
}

const SOURCES = ['PubMed', 'TinyFish Search', 'TinyFish Fetch', 'TinyFish Agent', 'ClinicalTrials.gov', 'DailyMed', 'Ollama', 'NetworkX', 'FastAPI']

export function Marquee() {
  const row = [...SOURCES, ...SOURCES]
  return (
    <div className="overflow-hidden border-b border-white/[0.06] py-5" aria-label="Data sources and tools">
      <div className="marquee flex w-max items-center gap-12">
        {row.map((s, i) => <span key={i} className="font-serif text-lg text-muted/80" aria-hidden={i >= SOURCES.length}>{s}</span>)}
      </div>
    </div>
  )
}

function Panel({ icon, title, sub, children }: { icon: ReactNode; title: string; sub: string; children: ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }} className="card flex h-full flex-col p-5">
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet/25 text-[#b6adf5]">{icon}</span>
        <div><h3 className="text-lg leading-tight">{title}</h3><p className="text-xs text-muted">{sub}</p></div>
      </div>
      <div className="mt-4 flex-1">{children}</div>
    </motion.div>
  )
}

export function Overview({ stats, drugs }: { stats: Stats | null; drugs: DrugSummary[] }) {
  const weights = Object.entries(stats?.weights ?? {})
  const conflicted = drugs.filter((d) => d.n_conflicts > 0).sort((a, b) => b.n_conflicts - a.n_conflicts).slice(0, 4)
  const tf = stats?.tinyfish ?? {}
  return (
    <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <p className="caps text-teal">Product overview</p>
      <h2 className="mt-2 max-w-2xl text-3xl sm:text-4xl">Every rank comes with its evidence, its doubts and its reason.</h2>
      <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Panel icon={<Gauge size={18} aria-hidden />} title="Graded evidence" sub="how a claim earns its 0-100">
          <ul className="space-y-2.5">
            {weights.map(([k, v]) => (
              <li key={k}>
                <div className="flex justify-between text-xs"><span className="capitalize text-muted">{k}</span><span className="tnum">{v}</span></div>
                <div className="mt-1 h-1.5 rounded-full bg-white/10"><motion.div initial={{ width: 0 }} animate={{ width: `${v * 3.4}%` }} transition={{ duration: 0.8 }} className="h-full rounded-full bg-gradient-to-r from-violet to-teal" /></div>
              </li>
            ))}
            {!weights.length && <Skeleton className="h-28" />}
          </ul>
        </Panel>
        <Panel icon={<ShieldAlert size={18} aria-hidden />} title="Guardrails" sub="what the system refuses to do">
          <ul className="space-y-2.5 text-sm">
            {['A claim without an exact source quote is discarded', 'Contradictions are shown side by side, never merged', 'Suppressors get a safety flag, not a hidden score', 'Missing evidence reads "unknown", not zero'].map((t) => (
              <li key={t} className="flex gap-2"><Check size={16} className="mt-0.5 shrink-0 text-teal" aria-hidden /><span className="text-muted">{t}</span></li>
            ))}
          </ul>
        </Panel>
        <Panel icon={<SplitSquareHorizontal size={18} aria-hidden />} title="Conflict inbox" sub="where papers disagree">
          <ul className="space-y-2">
            {conflicted.map((d) => (
              <li key={d.drug}>
                <Link to={`/drug/${encodeURIComponent(d.drug)}`} className="flex items-center justify-between rounded-lg border border-white/[0.07] px-3 py-2 text-sm transition-colors hover:border-coral/40">
                  <span className="capitalize">{d.drug}</span><Badge tone="coral">{d.n_conflicts} conflict{d.n_conflicts > 1 ? 's' : ''}</Badge>
                </Link>
              </li>
            ))}
            {!conflicted.length && <Skeleton className="h-28" />}
          </ul>
        </Panel>
        <Panel icon={<Globe size={18} aria-hidden />} title="Multi-source pipeline" sub="live TinyFish calls">
          <ul className="space-y-3">
            {(['search', 'fetch', 'agent'] as const).map((k) => (
              <li key={k} className="flex items-center justify-between rounded-lg bg-white/[0.04] px-3 py-2.5">
                <span className="text-sm capitalize text-muted">{k}</span>
                <span className="font-serif text-2xl">{tf[k] ? <CountUp value={tf[k].live} /> : '–'}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </section>
  )
}

export function Insights({ stats, drugs }: { stats: Stats | null; drugs: DrugSummary[] }) {
  const top = [...drugs].filter((d) => d.n_claims > 0).sort((a, b) => b.score - a.score)
  const chart = top.slice(0, 10).map((d) => ({ name: d.drug, score: Math.round(d.score) }))
  const v = stats?.validation
  const agent = stats?.tinyfish?.agent
  const kpis: [string, number | undefined, string][] = [
    ['Papers with claims', stats?.papers_with_claims, 'of ' + (stats?.papers ?? '…') + ' processed'],
    ['Verified claims', stats?.claims_verified, 'exact-quote grounded'],
    ['Conflicts flagged', stats?.conflicts, 'shown side by side'],
    ['Controls recovered', v?.recovered, v ? `of ${v.total} known controls` : ''],
  ]
  return (
    <section className="mx-auto max-w-6xl px-4 pb-14 sm:px-6">
      <p className="caps text-teal">Insights</p>
      <h2 className="mt-2 text-3xl sm:text-4xl">The corpus at a glance</h2>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map(([label, val, sub]) => (
          <div key={label} className="card p-5">
            <p className="caps">{label}</p>
            <p className="mt-2 font-serif text-4xl">{val === undefined ? <Skeleton className="h-10 w-20" /> : <CountUp value={val} />}</p>
            <p className="mt-1 text-xs text-muted">{sub}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="card p-5">
          <div className="flex items-center justify-between"><p className="caps">Top drugs by score</p><span className="text-xs text-muted">0-100, evidence-graded</span></div>
          <div className="mt-4 h-64" role="img" aria-label="Bar chart of the ten highest drug scores">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fill: '#9a97c4', fontSize: 11 }} tickLine={false} axisLine={false} interval={0} angle={-30} textAnchor="end" height={56} />
                <YAxis tick={{ fill: '#9a97c4', fontSize: 11 }} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ background: '#13112b', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, color: '#f1f0fa' }} />
                <Bar dataKey="score" radius={[6, 6, 0, 0]} isAnimationActive>
                  {chart.map((c) => <Cell key={c.name} fill={scoreColor(c.score)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card p-5">
          <p className="caps">TinyFish Agent runs</p>
          <p className="mt-3 font-serif text-4xl">{agent ? <CountUp value={agent.live} /> : '–'}<span className="text-lg text-muted"> live runs</span></p>
          <div className="mt-4 h-2 rounded-full bg-white/10" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, agent && agent.live ? ((agent.live - agent.errors) / agent.live) * 100 : 0)} aria-label="Share of agent runs that completed">
            <motion.div initial={{ width: 0 }} animate={{ width: `${Math.min(100, agent && agent.live ? ((agent.live - agent.errors) / agent.live) * 100 : 0)}%` }} transition={{ duration: 0.9 }} className="h-full rounded-full bg-gradient-to-r from-teal to-violet" />
          </div>
          <p className="mt-3 text-xs text-muted">Agent runs drive ClinicalTrials.gov and drug-label pages that have no API. The bar is the share of runs that completed. Each run is capped per process and every call is logged.</p>
          <p className="mt-3 text-xs text-muted">{agent ? `${agent.errors} failed or timed out, ${agent.cached} served from cache.` : ''}</p>
        </div>
      </div>
      <div className="card mt-4 overflow-hidden">
        <div className="flex items-center justify-between px-5 pt-5"><p className="caps">Leaderboard</p><span className="text-xs text-muted">top 8 of {top.length} scored</span></div>
        <div className="overflow-x-auto">
          <table className="mt-3 w-full min-w-[560px] text-left text-sm">
            <thead className="text-xs text-muted"><tr><th className="px-5 py-2 font-medium">#</th><th className="py-2 font-medium">Drug</th><th className="py-2 font-medium">Score</th><th className="py-2 font-medium">Claims</th><th className="py-2 font-medium">Conflicts</th><th className="py-2 font-medium">Confidence</th><th className="px-5 py-2" /></tr></thead>
            <tbody>
              {top.slice(0, 8).map((d) => (
                <tr key={d.drug} className="border-t border-white/[0.06] transition-colors hover:bg-white/[0.03]">
                  <td className="tnum px-5 py-3 text-muted">{d.rank}</td>
                  <td className="py-3 font-medium capitalize">{d.drug}{d.category !== 'candidate' && <span className="ml-2 text-xs font-normal text-muted">{d.category === 'control_pos' ? 'positive control' : 'negative control'}</span>}</td>
                  <td className="tnum py-3"><span style={{ color: scoreColor(d.score) }}>{d.score.toFixed(0)}</span></td>
                  <td className="tnum py-3"><span className="inline-flex items-center gap-1"><FlaskConical size={13} className="text-muted" aria-hidden />{d.n_claims}</span></td>
                  <td className="tnum py-3">{d.n_conflicts || '–'}</td>
                  <td className="py-3"><ConfidenceBadge label={d.confidence_label} /></td>
                  <td className="px-5 py-3 text-right"><Link to={`/drug/${encodeURIComponent(d.drug)}`} className="inline-flex text-muted hover:text-teal" aria-label={`Open ${d.drug}`}><ArrowUpRight size={16} aria-hidden /></Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export function ClosingCta() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-6 sm:px-6">
      <div className="card noise relative overflow-hidden p-8 text-center sm:p-12">
        <div className="absolute left-1/2 top-0 h-48 w-[480px] -translate-x-1/2 rounded-full bg-violet/30 blur-[100px]" aria-hidden />
        <h2 className="relative text-3xl sm:text-4xl">See why a drug ranks where it does.</h2>
        <p className="relative mx-auto mt-3 max-w-xl text-muted">Open any drug to read the verbatim quotes, the conflicts and the score breakdown, or walk the graph from a drug to its pathways and stages.</p>
        <div className="relative mt-6 flex flex-wrap justify-center gap-3">
          <button onClick={() => scrollTo('ranking')} className="inline-flex items-center gap-2 rounded-xl bg-teal px-5 py-3 text-sm font-semibold text-ink">Browse the ranking <ArrowRight size={16} aria-hidden /></button>
          <Link to="/methods" className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/[0.04] px-5 py-3 text-sm font-medium hover:bg-white/10">How it is validated</Link>
        </div>
      </div>
    </section>
  )
}
