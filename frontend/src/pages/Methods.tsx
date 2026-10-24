import { motion } from 'framer-motion'
import { ArrowRight, CheckCircle2, Fish, XCircle } from 'lucide-react'
import { Bar, Badge, CountUp, ErrorBox, Reveal, Skeleton, pretty } from '../ui'
import { fetchStats, useAsync, type Stats } from '../api'

const palette = ['var(--teal)', 'var(--violet)', 'var(--amber)', 'var(--coral)', '#8c86d9']
const weightNames: Record<string, string> = {
  replication: 'Replication across papers', design: 'Study design', markers: 'Marker validity', species: 'Species relevance', dose: 'Dose / BBB plausibility',
}

function Weights({ stats }: { stats: Stats }) {
  const entries = Object.entries(stats.weights)
  return (
    <section className="card p-6" aria-label="Scoring weights">
      <h2 className="text-xl">How a claim is scored</h2>
      <p className="mt-1 text-sm text-muted">Each verified claim gets a 0–100 confidence from five weighted components, minus penalties.</p>
      <div className="mt-5 flex h-4 overflow-hidden rounded-full bg-white/[0.07]" role="img" aria-label="Stacked weights bar">
        {entries.map(([k, v], i) => (
          <motion.div key={k} style={{ background: palette[i] }} initial={{ width: 0 }} animate={{ width: `${v}%` }} transition={{ duration: 0.6, delay: i * 0.06 }} title={`${weightNames[k]}: ${v}`} />
        ))}
      </div>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2">
        {entries.map(([k, v], i) => (
          <li key={k} className="flex items-center justify-between rounded-lg bg-white/[0.03] px-3 py-2 text-sm">
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: palette[i] }} />{weightNames[k] ?? k}</span>
            <span className="tnum text-muted">{v}</span>
          </li>
        ))}
      </ul>
      <p className="caps mt-5">Penalties</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {Object.entries(stats.penalties).map(([k, v]) => <Badge key={k} tone="coral">−{v} {pretty(k)}</Badge>)}
      </div>
    </section>
  )
}

function Validation({ stats }: { stats: Stats }) {
  const v = stats.validation
  const ev = stats.extraction_eval
  return (
    <section className="card p-6" aria-label="Validation">
      <h2 className="text-xl">Validation against controls</h2>
      {!v ? (
        <p className="mt-3 text-sm text-muted">Validation has not been run yet (<code>python scripts/validate.py</code>).</p>
      ) : (
        <>
          <p className="mt-1 text-sm text-muted">
            Positive controls should surface pro-neurogenic evidence; negative controls should surface suppression or safety flags. Disagreements are reported, not tuned away.
          </p>
          <p className="mt-4 font-serif text-3xl"><CountUp value={v.recovered} /> <span className="text-muted">of {v.total} controls as expected</span></p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead><tr className="caps"><th className="py-2 pr-3 font-semibold">Drug</th><th className="pr-3 font-semibold">Expected</th><th className="pr-3 font-semibold">Observed</th><th className="pr-3 font-semibold">Score</th><th className="font-semibold">Match</th></tr></thead>
              <tbody className="divide-y divide-white/[0.06]">
                {v.controls.map((c) => (
                  <tr key={c.drug}>
                    <td className="py-2.5 pr-3 capitalize">{c.drug}</td>
                    <td className="pr-3 text-muted">{c.expected}</td>
                    <td className="pr-3 text-muted">{c.observed}</td>
                    <td className="tnum pr-3">{c.score.toFixed(0)}</td>
                    <td>{c.ok ? <CheckCircle2 size={17} className="text-teal" aria-label="Matches" /> : <XCircle size={17} className="text-coral" aria-label="Does not match" />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {v.ablation.length > 0 && (
            <div className="mt-6">
              <h3 className="caps">Ablation: ranking with vs. without evidence grading</h3>
              <div className="mt-3 space-y-3">
                {v.ablation.map((a) => (
                  <Bar key={a.label} label={a.label} display={`gap ${a.separation.toFixed(1)} ranks`} value={Math.max(0, Math.min(100, (a.separation / Math.max(...v.ablation.map((x) => x.separation), 1)) * 100))} color={a.label.startsWith('With') ? 'var(--teal)' : 'var(--muted)'} />
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">Gap = mean rank of negative controls minus mean rank of positive controls; a longer bar means positives sit further above negatives. Plain vote counts are a strong baseline on this small control set.</p>
            </div>
          )}
        </>
      )}
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-white/[0.03] p-4">
          <p className="caps">Claims with verified quote</p>
          <p className="mt-1 font-serif text-3xl">{v?.quote_verified_fraction != null ? `${(v.quote_verified_fraction * 100).toFixed(0)}%` : 'unknown'}</p>
          <p className="mt-1 text-xs text-muted">Unverified claims are discarded, never shown.</p>
        </div>
        <div className="rounded-xl bg-white/[0.03] p-4">
          <p className="caps">Extraction vs. gold set (AI-labelled)</p>
          {ev && typeof ev.claim_detection === 'object' ? (
            <p className="mt-1 font-serif text-3xl">P {(ev.claim_detection.precision * 100).toFixed(0)}% · R {(ev.claim_detection.recall * 100).toFixed(0)}%</p>
          ) : <p className="mt-1 font-serif text-3xl text-muted">unknown</p>}
          <p className="mt-1 text-xs text-muted">{ev ? `n = ${ev.n_gold as number} sentences, labelled by Claude (not a human annotator); direction F1 ${typeof ev.direction === 'object' ? (ev.direction.f1 * 100).toFixed(0) : '?'}%` : 'Gold set not labelled yet.'}</p>
        </div>
      </div>
    </section>
  )
}

function TinyFishPanel({ stats }: { stats: Stats }) {
  const rows = [['Search', 'search', 'Ranked URLs per drug × stage'], ['Fetch', 'fetch', 'Open-access pages → clean Markdown'], ['Agent', 'agent', 'ClinicalTrials.gov + drug labels']] as const
  return (
    <section className="card relative overflow-hidden p-6" aria-label="Powered by TinyFish">
      <div className="absolute -right-16 -top-16 h-52 w-52 rounded-full bg-teal/20 blur-[80px]" aria-hidden />
      <h2 className="relative flex items-center gap-2 text-xl"><Fish size={20} className="text-teal" aria-hidden /> Powered by TinyFish</h2>
      <p className="relative mt-1 text-sm text-muted">Real call counts from this pipeline's own call log.</p>
      <div className="relative mt-5 grid gap-3 sm:grid-cols-3">
        {rows.map(([label, key, note]) => {
          const u = stats.tinyfish[key] ?? { live: 0, cached: 0, errors: 0 }
          return (
            <div key={key} className="rounded-xl bg-white/[0.04] p-4">
              <p className="caps">{label}</p>
              <p className="mt-1 font-serif text-4xl"><CountUp value={u.live} /></p>
              <p className="text-xs text-muted">live calls · {u.cached} cache hits · {u.errors} errors</p>
              <p className="mt-2 text-sm">{note}</p>
            </div>
          )
        })}
      </div>
      <ol className="relative mt-6 flex flex-wrap items-center gap-2 text-sm">
        {['TinyFish Search', 'TinyFish Fetch', 'PubMed abstracts', `Extract (${stats.extractor_model})`, 'Quote check', 'Grade', 'Rank + graph'].map((s, i, a) => (
          <li key={s} className="flex items-center gap-2"><span className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5">{s}</span>{i < a.length - 1 && <ArrowRight size={14} className="text-muted" aria-hidden />}</li>
        ))}
      </ol>
    </section>
  )
}

export default function Methods() {
  const { data, error, loading } = useAsync(fetchStats, [])
  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <Reveal>
        <p className="caps text-teal">Methods &amp; validation</p>
        <h1 className="mt-2 text-4xl font-semibold sm:text-5xl">Transparent by design</h1>
        <p className="mt-3 max-w-2xl text-muted">A readable score beats an unexplained embedding. Every number below is computed from verified, quoted evidence.</p>
      </Reveal>
      <div className="mt-8 space-y-6">
        {error && <ErrorBox message={error} />}
        {loading && <><Skeleton className="h-64" /><Skeleton className="h-80" /></>}
        {data && (
          <>
            <TinyFishPanel stats={data} />
            <Weights stats={data} />
            <Validation stats={data} />
            <section className="card border-amber/25 p-6" aria-label="Honesty statement">
              <h2 className="text-xl">Honesty statement</h2>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-text/90">
                <li>Every output is a <strong>hypothesis for lab testing</strong>, never a treatment claim.</li>
                <li>No paper, PMID, dose, quote or number is invented. Missing data is shown as “unknown”, not as “no effect”.</li>
                <li>A claim is kept only if its quote is an exact substring of the source text.</li>
                <li>Species and study design come from the claim's own quote, else the paper's dominant animal species; “human” is assigned only when the quote says so.</li>
                <li>The corpus is small and abstract-heavy; absence of a claim is absence of extracted evidence, not evidence of absence.</li>
              </ul>
            </section>
          </>
        )}
      </div>
    </main>
  )
}
