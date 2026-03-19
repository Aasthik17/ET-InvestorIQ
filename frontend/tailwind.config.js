/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Indian market color scheme
        bull: '#00C896',
        bear: '#FF4757',
        accent: '#0066FF',
        'accent-light': '#4D94FF',
        neutral: '#1A1A2E',
        card: '#16213E',
        border: '#0F3460',
        surface: '#0D1117',
        muted: '#8B949E',
        'text-base': '#E6EDF3',
        gold: '#FFD700',
        neon: '#00FF88',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-card': 'linear-gradient(135deg, #16213E 0%, #0F3460 100%)',
        'gradient-bull': 'linear-gradient(135deg, #00C896 0%, #00FF88 100%)',
        'gradient-bear': 'linear-gradient(135deg, #FF4757 0%, #FF6B81 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-in': 'slideIn 0.4s ease-out',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
        'ticker': 'ticker 30s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0, 200, 150, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(0, 200, 150, 0.7)' },
        },
        ticker: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(-100%)' },
        },
      },
      boxShadow: {
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 8px 32px rgba(0, 102, 255, 0.2)',
        'bull': '0 0 16px rgba(0, 200, 150, 0.3)',
        'bear': '0 0 16px rgba(255, 71, 87, 0.3)',
      },
    },
  },
  plugins: [],
}
