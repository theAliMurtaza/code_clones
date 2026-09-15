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
        bg:      '#f6f8fc',
        surface: '#ffffff',
        s2:      '#f3f6fb',
        s3:      '#e8edf5',
        b1:      '#e6ebf2',
        b2:      '#cfd8e6',
        accent:  '#2563eb',
        emerald: '#059669',
        violet:  '#7c3aed',
        amber:   '#d97706',
        rose:    '#e11d48',
        success: '#059669',
        t1:      '#162033',
        t2:      '#58677c',
        t3:      '#8795a9',
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
