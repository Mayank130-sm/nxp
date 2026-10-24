/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: 'rgb(var(--ink-rgb) / <alpha-value>)',
        night: 'rgb(var(--night-rgb) / <alpha-value>)',
        surface: 'rgb(var(--surface-rgb) / <alpha-value>)',
        text: 'rgb(var(--text-rgb) / <alpha-value>)',
        muted: 'rgb(var(--muted-rgb) / <alpha-value>)',
        teal: 'rgb(var(--teal-rgb) / <alpha-value>)',
        violet: 'rgb(var(--violet-rgb) / <alpha-value>)',
        amber: 'rgb(var(--amber-rgb) / <alpha-value>)',
        coral: 'rgb(var(--coral-rgb) / <alpha-value>)',
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
