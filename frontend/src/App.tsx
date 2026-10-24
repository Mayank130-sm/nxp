import { Brain, ChevronsRight } from 'lucide-react'
import { NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import Home from './pages/Home'
import DrugPage from './pages/DrugPage'
import GraphPage from './pages/GraphPage'
import Methods from './pages/Methods'
import { ClosingCta } from './landing'

const links = [
  { to: '/', label: 'Ranking' },
  { to: '/graph', label: 'Graph' },
  { to: '/methods', label: 'Methods' },
]

function ScrollTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

export default function App() {
  const navigate = useNavigate()
  const getStarted = () => {
    navigate('/')
    window.setTimeout(() => document.getElementById('ranking')?.scrollIntoView({ behavior: 'smooth' }), 120)
  }
  return (
    <div className="min-h-screen">
      <ScrollTop />
      <header className="sticky top-0 z-30 border-b border-white/10 bg-black/60 backdrop-blur-xl">
        <nav className="mx-auto grid h-16 max-w-[1400px] grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-8" aria-label="Primary">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-semibold uppercase tracking-wide" style={{ fontFamily: 'Inter, sans-serif' }}>
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-black"><Brain size={18} aria-hidden /></span>
            NeuroRx
          </NavLink>
          <ul className="flex items-center gap-1 sm:gap-4">
            {links.map((l) => (
              <li key={l.to}>
                <NavLink
                  to={l.to}
                  end={l.to === '/'}
                  className={({ isActive }) =>
                    `rounded-lg px-2.5 py-1.5 text-sm transition-colors sm:px-3 sm:text-base ${isActive ? 'text-white' : 'text-white/60 hover:text-white'}`
                  }
                >
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="flex justify-end">
            <button onClick={getStarted} className="hidden items-center gap-2 rounded-full border border-white/40 bg-black px-5 py-2 text-sm font-semibold uppercase tracking-wide shadow-[inset_0_1px_0_rgba(255,255,255,0.25)] transition-colors hover:bg-white/10 sm:inline-flex">
              Get started <ChevronsRight size={15} aria-hidden />
            </button>
          </div>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/drug/:name" element={<DrugPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/methods" element={<Methods />} />
      </Routes>
      <ClosingCta />
      <footer className="mx-auto mt-10 max-w-6xl border-t border-white/[0.07] px-4 py-8 text-xs text-muted sm:px-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row">
          <div>
            <p className="flex items-center gap-2 font-serif text-base text-text"><Brain size={16} className="text-teal" aria-hidden /> NeuroRx</p>
            <p className="mt-2 max-w-md">Outputs are hypotheses for lab testing, not treatment claims. Every claim links to its source paper.</p>
          </div>
          <ul className="flex gap-5">
            {links.map((l) => <li key={l.to}><NavLink to={l.to} end={l.to === '/'} className="hover:text-text">{l.label}</NavLink></li>)}
            <li><a href="https://github.com/Mayank130-sm/nxp" target="_blank" rel="noreferrer" className="hover:text-text">GitHub</a></li>
          </ul>
        </div>
      </footer>
    </div>
  )
}
