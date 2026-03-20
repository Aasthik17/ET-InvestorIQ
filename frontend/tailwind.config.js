/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    // Override defaults where needed
    borderRadius: {
      none: '0',
      sm: '3px',
      DEFAULT: '4px',
      md: '6px',
      full: '9999px',
    },
    extend: {
      colors: {
        // ── Backgrounds ──────────────────────────────────────────────────
        bg: {
          primary:   '#131722',
          secondary: '#1E222D',
          tertiary:  '#2A2E39',
          hover:     '#363A45',
          input:     '#2A2E39',
        },
        // ── Borders ──────────────────────────────────────────────────────
        border: {
          DEFAULT: '#2A2E39',
          strong:  '#363A45',
          light:   '#1E222D',
        },
        // ── Text ─────────────────────────────────────────────────────────
        text: {
          primary:   '#D1D4DC',
          secondary: '#787B86',
          muted:     '#4C525E',
          inverse:   '#131722',
        },
        // ── Semantic financial colors ─────────────────────────────────────
        bull:    '#26A69A',
        bear:    '#EF5350',
        neutral: '#787B86',
        // ── Interactive ───────────────────────────────────────────────────
        accent: {
          DEFAULT: '#2962FF',
          hover:   '#1E53E5',
          subtle:  '#1E2B4D',
        },
        // ── Signal type colors ────────────────────────────────────────────
        signal: {
          insider:   '#F59E0B',
          filing:    '#8B5CF6',
          technical: '#06B6D4',
          fii:       '#10B981',
          corporate: '#EC4899',
        },
        // ── Chart-specific ────────────────────────────────────────────────
        chart: {
          grid:      '#1E222D',
          crosshair: '#363A45',
        },
        // ── Brand ─────────────────────────────────────────────────────────
        et: '#F26522',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs':  ['10px', { lineHeight: '14px' }],
        xs:     ['11px', { lineHeight: '16px' }],
        sm:     ['12px', { lineHeight: '18px' }],
        base:   ['13px', { lineHeight: '20px' }],
        md:     ['14px', { lineHeight: '22px' }],
        lg:     ['16px', { lineHeight: '24px' }],
        xl:     ['18px', { lineHeight: '28px' }],
        '2xl':  ['22px', { lineHeight: '32px' }],
      },
      spacing: {
        '13': '52px',
        '15': '60px',
        '18': '72px',
      },
      boxShadow: {
        none: 'none',
        card: 'none',
      },
      animation: {
        spin: 'spin 0.8s linear infinite',
        'fade-in': 'fadeIn 200ms ease-out',
        'slide-down': 'slideDown 200ms ease-out',
        'progress': 'progress 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideDown: {
          '0%':   { opacity: '0', maxHeight: '0' },
          '100%': { opacity: '1', maxHeight: '500px' },
        },
        progress: {
          '0%':   { width: '0%' },
          '50%':  { width: '70%' },
          '100%': { width: '90%' },
        },
      },
    },
  },
  plugins: [],
}
