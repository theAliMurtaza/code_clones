/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        /* ── Dark Theme Palette ── */
        bg:      '#0d1117',   /* deep GitHub-style dark */
        surface: '#161b22',   /* card backgrounds */
        s2:      '#1c2330',   /* slightly lighter surface */
        s3:      '#222c3a',   /* hover / subtle fill */
        b1:      '#2a3448',   /* border default */
        b2:      '#3a4a60',   /* border hover */
        accent:  '#3b82f6',   /* vibrant blue */
        emerald: '#10b981',   /* green */
        violet:  '#a78bfa',   /* purple */
        amber:   '#f59e0b',   /* orange/amber */
        rose:    '#f43f5e',   /* red/rose */
        success: '#22c55e',   /* success green */
        t1:      '#e8edf5',   /* primary text — near white */
        t2:      '#94a9c9',   /* secondary text — slate-blue */
        t3:      '#5e7494',   /* muted text */
      },
      keyframes: {
        fadeUp:  { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideIn: { from: { transform: 'translateX(110%)', opacity: 0 }, to: { transform: 'translateX(0)', opacity: 1 } },
        pulse2:  { '0%,100%': { opacity: .4 }, '50%': { opacity: 1 } },
        spin:    { to: { transform: 'rotate(360deg)' } },
        shimmer: { from: { backgroundPosition: '-200% 0' }, to: { backgroundPosition: '200% 0' } },
      },
      animation: {
        fadeUp:  'fadeUp .3s cubic-bezier(.22,1,.36,1) both',
        slideIn: 'slideIn .3s ease both',
        pulse2:  'pulse2 2.2s ease infinite',
        spin:    'spin 1s linear infinite',
        shimmer: 'shimmer 2s linear infinite',
      },
    },
  },
  plugins: [],
}
