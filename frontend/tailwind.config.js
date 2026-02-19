/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#070b12',
          800: '#0d1522',
          700: '#162235',
          600: '#20314a',
          500: '#2e4668',
          400: '#4b6287',
          300: '#7086ab',
        },
        accent: {
          primary: '#2dd4bf',
          secondary: '#38bdf8',
          tertiary: '#0ea5a1',
          glow: 'rgba(45, 212, 191, 0.24)',
        },
        success: {
          DEFAULT: '#22c55e',
          dark: '#16a34a',
          glow: 'rgba(34, 197, 94, 0.22)',
        },
        warning: {
          DEFAULT: '#f59e0b',
          dark: '#d97706',
          glow: 'rgba(245, 158, 11, 0.22)',
        },
        danger: {
          DEFAULT: '#f43f5e',
          dark: '#e11d48',
          glow: 'rgba(244, 63, 94, 0.22)',
        },
        neutral: {
          100: '#f8fafc',
          200: '#dbe7ff',
          300: '#afc3e7',
          400: '#8499bc',
          500: '#5f7392',
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 24px rgba(56, 189, 248, 0.3)',
        'glow-green': '0 0 24px rgba(34, 197, 94, 0.3)',
        'glow-orange': '0 0 24px rgba(245, 158, 11, 0.3)',
        'glow-red': '0 0 24px rgba(244, 63, 94, 0.3)',
        'card': '0 14px 48px rgba(2, 8, 23, 0.48)',
        'card-hover': '0 20px 60px rgba(2, 8, 23, 0.62)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(circle at center, var(--tw-gradient-stops))',
        'grid-pattern': 'linear-gradient(rgba(56, 189, 248, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 189, 248, 0.08) 1px, transparent 1px)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2.2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 6px rgba(45, 212, 191, 0.25)' },
          '100%': { boxShadow: '0 0 24px rgba(56, 189, 248, 0.4)' },
        },
      },
    },
  },
  plugins: [],
}
