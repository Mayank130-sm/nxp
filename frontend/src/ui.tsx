import { animate, motion, useReducedMotion } from 'framer-motion'
import { AlertTriangle, FlaskConical, ShieldAlert, SplitSquareHorizontal } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'

export const scoreColor = (s: number) => (s >= 55 ? 'var(--teal)' : s >= 30 ? 'var(--amber)' : 'var(--muted)')

export const pretty = (s: string | null | undefined) => (s ? s.replace(/_/g, ' ') : 'unknown')

export function CountUp({ value, decimals = 0, className }: { value: number; decimals?: number; className?: string }) {
  const reduce = useReducedMotion()
  const [shown, setShown] = useState(reduce ? value : 0)
  useEffect(() => {
    if (reduce) {
      setShown(value)
      return
    }
    const c = animate(0, value, { duration: 0.6, ease: 'easeOut', onUpdate: (v) => setShown(v) })
    return () => c.stop()
  }, [value, reduce])
  return <span className={`tnum ${className ?? ''}`}>{shown.toFixed(decimals)}</span>
}

export function ScoreRing({ score, size = 72, stroke = 6 }: { score: number; size?: number; stroke?: number }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const color = scoreColor(score)
  return (
    <div className="relative shrink-0" style={{ width: size, height: size, color }} role="img" aria-label={`Score ${score.toFixed(0)} out of 100`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - score / 100) }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center font-serif text-text" style={{ fontSize: size * 0.3 }}>
        <CountUp value={score} />
      </div>
    </div>
  )
}

export function Bar({ label, value, color = 'var(--violet)', hint, display }: { label: string; value: number; color?: string; hint?: string; display?: string }) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between text-sm">
        <span className="text-text">{label}</span>
        <span className="tnum text-muted">{display ?? `${value.toFixed(0)}%`}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/[0.07]" title={hint}>
        <motion.div className="h-full rounded-full" style={{ background: color }} initial={{ width: 0 }} animate={{ width: `${Math.min(100, value)}%` }} transition={{ duration: 0.6, ease: 'easeOut' }} />
      </div>
    </div>
  )
}

type Tone = 'teal' | 'violet' | 'amber' | 'coral' | 'muted'
const tones: Record<Tone, string> = {
  teal: 'bg-teal/15 text-teal border-teal/30',
  violet: 'bg-violet/20 text-[#b6adf5] border-violet/40',
  amber: 'bg-amber/15 text-amber border-amber/30',
  coral: 'bg-coral/15 text-coral border-coral/30',
  muted: 'bg-white/5 text-muted border-white/10',
}
export function Badge({ tone = 'muted', icon, children }: { tone?: Tone; icon?: ReactNode; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {icon}
      {children}
    </span>
  )
}

export const ConflictBadge = ({ n }: { n: number }) => (
  <Badge tone="coral" icon={<SplitSquareHorizontal size={12} aria-hidden />}>{n} conflict{n > 1 ? 's' : ''}</Badge>
)
export const SafetyBadge = () => <Badge tone="coral" icon={<ShieldAlert size={12} aria-hidden />}>Safety flag</Badge>
export const EvidenceChip = ({ n }: { n: number }) => (
  <Badge tone="violet" icon={<FlaskConical size={12} aria-hidden />}>{n} claim{n !== 1 ? 's' : ''}</Badge>
)
export const ConfidenceBadge = ({ label }: { label: string }) => (
  <Badge tone={label === 'high' ? 'teal' : label === 'moderate' ? 'amber' : 'muted'}>{label} confidence</Badge>
)

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-white/[0.06] ${className}`} aria-hidden />
}

export function Reveal({ children, delay = 0, className = '' }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay, ease: 'easeOut' }}>
      {children}
    </motion.div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div role="alert" className="card flex items-start gap-3 border-coral/30 p-5">
      <AlertTriangle className="mt-0.5 shrink-0 text-coral" size={18} aria-hidden />
      <div>
        <p className="font-medium">Could not load data</p>
        <p className="text-sm text-muted">{message}. Start the API (<code>make dev</code>) or run <code>python scripts/export_static.py</code>.</p>
      </div>
    </div>
  )
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="card p-10 text-center">
      <p className="font-serif text-xl">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  )
}

export function Disclaimer() {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-amber/25 bg-amber/10 px-4 py-2.5 text-sm text-amber" role="note">
      <AlertTriangle size={16} aria-hidden className="shrink-0" />
      Hypothesis for lab testing, not a treatment claim.
    </div>
  )
}

export function useDebounced<T>(v: T, ms = 150): T {
  const [d, setD] = useState(v)
  const t = useRef<number>(0)
  useEffect(() => {
    t.current = window.setTimeout(() => setD(v), ms)
    return () => clearTimeout(t.current)
  }, [v, ms])
  return d
}
