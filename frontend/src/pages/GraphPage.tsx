import { AnimatePresence, motion } from 'framer-motion'
import { Crosshair, Maximize2, Minus, Plus, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d'
import { Link } from 'react-router-dom'
import { fetchGraph, useAsync, type GraphData } from '../api'
import { Badge, Disclaimer, Empty, ErrorBox, Skeleton, pretty } from '../ui'

const COLORS = { drug: '#14A596', pathway: '#6B5BD2', stage: '#F2B84B', disease: '#F0645F' } as const
type GNode = GraphData['nodes'][number] & { x?: number; y?: number }
type GLink = Omit<GraphData['links'][number], 'source' | 'target'> & { source: string | GNode; target: string | GNode }
const idOf = (n: string | GNode) => (typeof n === 'string' ? n : n.id)

function useSize<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [size, setSize] = useState({ w: 800, h: 600 })
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver(([e]) => setSize({ w: e.contentRect.width, h: e.contentRect.height }))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, size] as const
}

export default function GraphPage() {
  const { data, error, loading } = useAsync(fetchGraph, [])
  const [wrap, size] = useSize<HTMLDivElement>()
  const fg = useRef<ForceGraphMethods<GNode, GLink> | undefined>(undefined)
  const [selected, setSelected] = useState<GNode | null>(null)
  const [hover, setHover] = useState<string | null>(null)
  const [focus, setFocus] = useState('')

  const graph = useMemo(() => {
    if (!data) return { nodes: [] as GNode[], links: [] as GLink[] }
    let nodes: GNode[] = data.nodes.map((n) => ({ ...n }))
    let links: GLink[] = data.links.map((l) => ({ ...l }))
    if (focus) {
      const keep = new Set([`drug:${focus}`])
      links.forEach((l) => { if (idOf(l.source) === `drug:${focus}`) keep.add(idOf(l.target)) })
      nodes = nodes.filter((n) => keep.has(n.id))
      links = links.filter((l) => keep.has(idOf(l.source)) && keep.has(idOf(l.target)))
    }
    return { nodes, links }
  }, [data, focus])

  useEffect(() => {
    const f = fg.current
    f?.d3Force('charge')?.strength(-220)
    f?.d3Force('link')?.distance(70)
  }, [graph])

  const neighbours = useMemo(() => {
    if (!selected) return []
    return graph.links.filter((l) => idOf(l.source) === selected.id || idOf(l.target) === selected.id)
      .map((l) => ({ l, other: graph.nodes.find((n) => n.id === (idOf(l.source) === selected.id ? idOf(l.target) : idOf(l.source))) }))
      .sort((a, b) => b.l.confidence - a.l.confidence)
  }, [selected, graph])

  const paint = useCallback((n: GNode, ctx: CanvasRenderingContext2D, scale: number) => {
    const r = n.type === 'drug' ? 3 + (n.score ?? 0) / 22 : n.type === 'disease' ? 7 : 5
    const color = COLORS[n.type]
    const flagged = n.type === 'drug' && n.safety_flag
    const active = hover === n.id || selected?.id === n.id
    ctx.beginPath(); ctx.arc(n.x ?? 0, n.y ?? 0, r, 0, 2 * Math.PI)
    ctx.fillStyle = color; ctx.shadowColor = color; ctx.shadowBlur = active ? 22 : 8; ctx.fill(); ctx.shadowBlur = 0
    if (flagged) { ctx.strokeStyle = '#F0645F'; ctx.lineWidth = 2.2 / scale; ctx.stroke() }
    if (active) { ctx.strokeStyle = '#F1F0FA'; ctx.lineWidth = 1.5 / scale; ctx.stroke() }
    if (scale > 1.1 || n.type !== 'drug' || active) {
      ctx.font = `${(n.type === 'drug' ? 11 : 12) / Math.max(scale, 0.9)}px Inter, sans-serif`
      ctx.textAlign = 'center'; ctx.fillStyle = 'rgba(241,240,250,0.92)'
      ctx.fillText(n.label, n.x ?? 0, (n.y ?? 0) + r + 10 / Math.max(scale, 0.9))
    }
  }, [hover, selected])

  const legend = [['Drug', COLORS.drug], ['Pathway', COLORS.pathway], ['Stage', COLORS.stage], ['Disease', COLORS.disease]]
  const drugs = (data?.nodes ?? []).filter((n) => n.type === 'drug').map((n) => n.label).sort()
  const btn = 'flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-surface/90 text-muted backdrop-blur hover:text-text'

  return (
    <main className="relative" style={{ height: 'calc(100vh - 56px)' }}>
      <div ref={wrap} className="absolute inset-0" aria-label="Knowledge graph canvas">
        {loading && <div className="p-6"><Skeleton className="h-full min-h-[60vh]" /></div>}
        {error && <div className="p-6"><ErrorBox message={error} /></div>}
        {data && graph.nodes.length <= 1 && <div className="p-6"><Empty title="The graph is empty" hint="Run the pipeline to extract claims first." /></div>}
        {data && graph.nodes.length > 1 && (
          <ForceGraph2D<GNode, GLink>
            ref={fg} width={size.w} height={size.h} graphData={graph} backgroundColor="rgba(0,0,0,0)"
            nodeCanvasObject={paint} nodePointerAreaPaint={(n, c, ctx) => { ctx.fillStyle = c; ctx.beginPath(); ctx.arc(n.x ?? 0, n.y ?? 0, 10, 0, 2 * Math.PI); ctx.fill() }}
            nodeLabel={(n) => `${n.label}${n.score !== undefined ? ` · score ${n.score.toFixed(0)}` : ''}`}
            linkWidth={(l) => (l.type === 'ranked_for' ? 0.35 : 0.8 + l.confidence / 24)} linkColor={(l) => (l.type === 'ranked_for' ? 'rgba(154,151,196,0.07)' : l.direction === 'decrease' ? 'rgba(240,100,95,0.6)' : 'rgba(154,151,196,0.42)')}
            linkDirectionalParticles={0} cooldownTicks={140} d3VelocityDecay={0.3} onEngineStop={() => fg.current?.zoomToFit(400, 90)}
            onNodeHover={(n) => setHover(n ? n.id : null)} onNodeClick={(n) => setSelected(n)} onBackgroundClick={() => setSelected(null)}
          />
        )}
      </div>

      <div className="pointer-events-none absolute left-4 top-4 flex max-w-[calc(100%-2rem)] flex-col gap-3 sm:left-6 sm:top-6">
        <div className="card pointer-events-auto px-4 py-3">
          <p className="caps mb-2">Legend</p>
          <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm">
            {legend.map(([k, c]) => <li key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: c, boxShadow: `0 0 8px ${c}` }} />{k}</li>)}
          </ul>
          <p className="mt-2 text-xs text-muted">Edge thickness = confidence. Coral edges = decreases. Coral ring = safety-flagged drug.</p>
        </div>
        <label className="card pointer-events-auto flex items-center gap-2 px-3 py-2 text-sm">
          <Crosshair size={15} className="text-muted" aria-hidden />
          <span className="sr-only">Focus on a drug</span>
          <select value={focus} onChange={(e) => { setFocus(e.target.value); setSelected(null) }} className="bg-transparent text-text outline-none">
            <option value="" className="bg-surface">Focus on a drug…</option>
            {drugs.map((d) => <option key={d} value={d} className="bg-surface">{d}</option>)}
          </select>
        </label>
      </div>

      <div className="absolute bottom-4 left-4 flex gap-2 sm:left-6" role="group" aria-label="Zoom controls">
        <button className={btn} aria-label="Zoom in" onClick={() => fg.current?.zoom((fg.current.zoom() ?? 1) * 1.4, 250)}><Plus size={16} /></button>
        <button className={btn} aria-label="Zoom out" onClick={() => fg.current?.zoom((fg.current.zoom() ?? 1) / 1.4, 250)}><Minus size={16} /></button>
        <button className={btn} aria-label="Reset view" onClick={() => { setFocus(''); fg.current?.zoomToFit(400, 60) }}><Maximize2 size={16} /></button>
      </div>
      <div className="pointer-events-none absolute bottom-4 right-4 hidden max-w-sm sm:block"><Disclaimer /></div>

      <AnimatePresence>
        {selected && (
          <motion.aside key={selected.id} initial={{ x: 380, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 380, opacity: 0 }} transition={{ duration: 0.3, ease: 'easeOut' }}
            className="card absolute bottom-0 right-0 top-0 z-20 w-full max-w-sm overflow-y-auto rounded-none border-y-0 border-r-0 p-5 sm:rounded-l-[20px]" aria-label="Node evidence">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="caps" style={{ color: COLORS[selected.type] }}>{selected.type}</p>
                <h2 className="mt-1 text-2xl capitalize">{selected.label}</h2>
                {selected.score !== undefined && <p className="tnum text-sm text-muted">Score {selected.score.toFixed(0)}{selected.safety_flag ? ' · safety flag' : ''}</p>}
              </div>
              <button onClick={() => setSelected(null)} aria-label="Close drawer" className="rounded-lg p-1.5 text-muted hover:bg-white/10 hover:text-text"><X size={18} /></button>
            </div>
            {selected.type === 'drug' && (
              <div className="mt-4 flex gap-2">
                <Link to={`/drug/${encodeURIComponent(selected.label)}`} className="rounded-lg bg-violet px-3.5 py-2 text-sm font-medium text-white hover:brightness-110">Open evidence</Link>
                <button onClick={() => setFocus(selected.label)} className="rounded-lg border border-white/10 px-3.5 py-2 text-sm hover:bg-white/5">Focus</button>
              </div>
            )}
            <h3 className="caps mt-6">Connections ({neighbours.length})</h3>
            <ul className="mt-2 space-y-2">
              {neighbours.map(({ l, other }) => (
                <li key={`${idOf(l.source)}-${idOf(l.target)}`} className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <button className="text-left font-medium capitalize hover:underline" onClick={() => other && setSelected(other)}>{other?.label}</button>
                    <Badge tone={l.direction === 'decrease' ? 'coral' : 'teal'}>{l.direction}</Badge>
                  </div>
                  <p className="tnum mt-1 text-muted">{pretty(l.type)} · confidence {l.confidence.toFixed(0)} · {l.n_claims} claim{l.n_claims !== 1 ? 's' : ''}</p>
                </li>
              ))}
            </ul>
          </motion.aside>
        )}
      </AnimatePresence>
    </main>
  )
}
