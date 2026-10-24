/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: 'var(--ink)',
        night: 'var(--night)',
        surface: 'var(--surface)',
        text: 'var(--text)',
        muted: 'var(--muted)',
        teal: 'var(--teal)',
        violet: 'var(--violet)',
        amber: 'var(--amber)',
        coral: 'var(--coral)',
      },
      fontFamily: {
        serif: ['Fraunces', 'Cormorant Garamond', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: { xl2: '20px' },
      boxShadow: {
        card: '0 1px 0 rgba(255,255,255,0.05) inset, 0 12px 32px -12px rgba(0,0,0,0.6), 0 2px 6px rgba(0,0,0,0.35)',
        glow: '0 0 0 1px rgba(107,91,210,0.35), 0 18px 48px -16px rgba(107,91,210,0.45)',
      },
    },
  },
  plugins: [],
}
