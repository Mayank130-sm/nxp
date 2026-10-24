import { ArrowLeft, BadgeCheck, ExternalLink, Pill, SplitSquareHorizontal } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { fetchDrug, useAsync, type Claim, type Conflict } from '../api'
import {
  Badge, Bar, ConfidenceBadge, ConflictBadge, Disclaimer, Empty, ErrorBox, EvidenceChip, Reveal, SafetyBadge, ScoreRing,
  Skeleton, pretty,
} from '../ui'

const dirTone = { increase: 'teal', decrease: 'coral', no_effect: 'muted', mixed: 'amber' } as const
const dirLabel = { increase: 'Increases', decrease: 'Decreases', no_effect: 'No effect', mixed: 'Mixed' } as const

function sourceLink(c: Claim) {
  if (c.pmid) return { href: `https://pubmed.ncbi.nlm.nih.gov/${c.pmid}/`, label: `PMID ${c.pmid}` }
  if (c.doi) return { href: `https://doi.org/${c.doi}`, label: `DOI ${c.doi}` }
  return c.source_url ? { href: c.source_url, label: 'Source' } : null
}

function Meta({ k, v }: { k: string; v: string | null }) {
  return (
    <div className="min-w-0">
      <dt className="caps">{k}</dt>
      <dd className="truncate text-sm" title={v ?? undefined}>{v ?? <span className="text-muted">unknown</span>}</dd>
    </div>
  )
}

function ClaimCard({ c, compact = false }: { c: Claim; compact?: boolean }) {
  const link = sourceLink(c)
  return (
    <article className="card p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={dirTone[c.direction]}>{dirLabel[c.direction]}</Badge>
        <Badge>{c.stage}</Badge>
        <span className="tnum ml-auto text-sm text-muted" title="Per-claim confidence (0-100)">conf {c.confidence.toFixed(0)}</span>
      </div>
      <blockquote className="mt-3 rounded-r-lg border-l-2 border-violet bg-violet/10 px-4 py-3 text-[15px] leading-relaxed">
        “<mark className="bg-amber/20 px-0.5 text-text">{c.evidence_quote}</mark>”
        <span className="ml-2 inline-flex items-center gap-1 align-middle text-xs text-teal" title="Quote verified as an exact substring of the source text">
          <BadgeCheck size={14} aria-hidden /> verified
        </span>
      </blockquote>
      <dl className={`mt-4 grid gap-3 ${compact ? 'grid-cols-2' : 'grid-cols-2 sm:grid-cols-4'}`}>
        <Meta k="Species" v={c.species} />
        <Meta k="Design" v={c.study_design ? pretty(c.study_design) : null} />
        <Meta k="Markers" v={c.markers} />
        <Meta k="Dose" v={c.dose} />
        <Meta k="Region" v={c.brain_region} />
        <Meta k="Duration" v={c.duration} />
      </dl>
      <div className="mt-4 flex items-start justify-between gap-3 border-t border-white/[0.07] pt-3 text-sm">
        <p className="line-clamp-2 text-muted">{c.title}{c.year ? ` (${c.year})` : ''}</p>
        {link && (
          <a href={link.href} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-1 text-violet hover:underline" style={{ color: '#b6adf5' }}>
            {link.label} <ExternalLink size={13} aria-hidden />
          </a>
        )}
      </div>
    </article>
  )
}

function ConflictPanel({ c }: { c: Conflict }) {
  const sides = Object.entries(c.sides)
  return (
    <section className="card border-coral/30 p-5" aria-label={`Conflict in ${c.stage}`}>
      <div className="mb-4 flex items-center gap-2">
        <SplitSquareHorizontal size={18} className="text-coral" aria-hidden />
        <h3 className="text-lg">Studies disagree: {c.stage}</h3>
        <Badge tone="coral">{c.severity}</Badge>
      </div>
      <div className={`grid gap-4 ${sides.length > 1 ? 'md:grid-cols-2' : ''}`}>
        {sides.map(([dir, claims]) => (
          <div key={dir} className="space-y-3">
            <p className="caps">{dirLabel[dir as keyof typeof dirLabel]} · {claims.length} claim{claims.length > 1 ? 's' : ''}</p>
            {claims.slice(0, 3).map((cl) => <ClaimCard key={cl.id} c={cl} compact />)}
          </div>
        ))}
      </div>
    </section>
  )
}

export default function DrugPage() {
  const { name = '' } = useParams()
  const { data: d, error, loading } = useAsync(() => fetchDrug(name), [name])

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text"><ArrowLeft size={15} aria-hidden /> All drugs</Link>
      {error && <div className="mt-6"><ErrorBox message={error} /></div>}
      {loading && <div className="mt-6 space-y-4"><Skeleton className="h-44" /><Skeleton className="h-64" /></div>}
      {d && (
        <>
          <Reveal className="card noise relative mt-6 overflow-hidden p-6 sm:p-8">
            <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-violet/25 blur-[90px]" aria-hidden />
            <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center">
              <ScoreRing score={d.score} size={120} stroke={9} />
              <div className="min-w-0 flex-1">
                <p className="caps">Rank #{d.rank} · {d.category === 'candidate' ? 'candidate' : d.category === 'control_pos' ? 'positive control' : 'negative control'}</p>
                <h1 className="mt-1 text-4xl font-semibold capitalize sm:text-5xl">{d.drug}</h1>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <ConfidenceBadge label={d.confidence_label} />
                  <EvidenceChip n={d.n_claims} />
                  {d.n_conflicts > 0 && <ConflictBadge n={d.n_conflicts} />}
                  {d.safety_flag && <SafetyBadge />}
                  {d.pathways.map((p) => <Badge key={p} tone="violet">{p}</Badge>)}
                </div>
                <p className="mt-4 max-w-3xl text-[15px] leading-relaxed text-text/90"><span className="caps mr-2">Why this rank</span>{d.why}</p>
              </div>
            </div>
          </Reveal>
          <div className="mt-4"><Disclaimer /></div>

          <div className="mt-8 grid gap-6 lg:grid-cols-3">
            <Reveal delay={0.1} className="card h-fit p-6 lg:col-span-1">
              <h2 className="text-xl">Score breakdown</h2>
              <p className="mt-1 text-sm text-muted">Average over pro-neurogenic claims, as a share of each component's maximum.</p>
              <div className="mt-5 space-y-4">
                <Bar label="Replication" value={d.breakdown.replication} color="var(--teal)" hint="Independent papers supporting the claim" />
                <Bar label="Study design" value={d.breakdown.design} />
                <Bar label="Marker validity" value={d.breakdown.markers} color="var(--amber)" hint="BrdU/Ki67 + DCX + NeuN beats a single marker" />
                <Bar label="Species relevance" value={d.breakdown.species} />
                <Bar label="Dose / BBB" value={d.breakdown.dose} color="var(--coral)" />
              </div>
            </Reveal>

            <div className="space-y-6 lg:col-span-2">
              {d.conflicts.map((c) => <ConflictPanel key={c.stage} c={c} />)}
              <section aria-label="Evidence">
                <h2 className="mb-3 text-xl">Evidence <span className="text-muted">({d.claims.length})</span></h2>
                {d.claims.length === 0 ? (
                  <Empty title="No verified claims yet" hint="Nothing in the corpus passed quote verification for this drug. Shown as unknown, not as no effect." />
                ) : (
                  <div className="space-y-3">{d.claims.map((c) => <ClaimCard key={c.id} c={c} />)}</div>
                )}
              </section>
            </div>
          </div>

          <div className="mt-8 grid gap-6 md:grid-cols-2">
            <section className="card p-6" aria-label="Clinical trials">
              <h2 className="flex items-center gap-2 text-xl"><Pill size={18} className="text-teal" aria-hidden /> Clinical trials</h2>
              {d.trials.length === 0 ? <p className="mt-3 text-sm text-muted">None retrieved (unknown, not none exist).</p> : (
                <ul className="mt-3 divide-y divide-white/[0.07]">
                  {d.trials.map((t) => (
                    <li key={t.nct_id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                      <a href={t.source_url} target="_blank" rel="noreferrer" className="tnum inline-flex items-center gap-1 hover:underline" style={{ color: '#b6adf5' }}>{t.nct_id} <ExternalLink size={12} aria-hidden /></a>
                      <span className="text-right text-muted">{t.phase ?? 'phase unknown'} · {t.status ?? 'status unknown'}</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="caps mt-4 normal-case tracking-normal">Source: ClinicalTrials.gov via TinyFish Agent</p>
            </section>
            <section className="card p-6" aria-label="Label notes">
              <h2 className="text-xl">Blood-brain barrier &amp; safety</h2>
              {d.notes ? (
                <dl className="mt-3 space-y-3 text-sm">
                  <div><dt className="caps">BBB</dt><dd>{d.notes.bbb_note ?? 'Not stated on label'}</dd></div>
                  <div><dt className="caps">Safety</dt><dd>{d.notes.safety_note ?? 'Not stated'}</dd></div>
                  {d.notes.source_url && <a href={d.notes.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline" style={{ color: '#b6adf5' }}>Label source <ExternalLink size={12} aria-hidden /></a>}
                </dl>
              ) : <p className="mt-3 text-sm text-muted">Not retrieved for this drug (unknown).</p>}
            </section>
          </div>
        </>
      )}
    </main>
  )
}
