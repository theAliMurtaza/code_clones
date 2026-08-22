/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        bg:      '#07090d',
        surface: '#0f1117',
        s2:      '#131920',
        s3:      '#1a2332',
        b1:      '#1e2d3d',
        b2:      '#243447',
        accent:  '#00d4ff',
        emerald: '#00e5b0',
        violet:  '#8b5cf6',
        amber:   '#f59e0b',
        rose:    '#f43f5e',
        success: '#10b981',
        t1:      '#e6edf3',
        t2:      '#8b949e',
        t3:      '#484f58',
      },
      keyframes: {
        fadeUp:  { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideIn: { from: { transform: 'translateX(110%)', opacity: 0 }, to: { transform: 'translateX(0)', opacity: 1 } },
        pulse2:  { '0%,100%': { opacity: .5 }, '50%': { opacity: 1 } },
        spin:    { to: { transform: 'rotate(360deg)' } },
      },
      animation: {
        fadeUp:  'fadeUp .3s cubic-bezier(.22,1,.36,1) both',
        slideIn: 'slideIn .3s ease both',
        pulse2:  'pulse2 2s ease infinite',
        spin:    'spin 1s linear infinite',
      },
    },
  },
  plugins: [],
}
