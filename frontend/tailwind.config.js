/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#fffbef',
          800: '#f7eede',
          700: '#fefbf0',
          600: '#e5e0d2',
          500: '#d4cfc1',
          400: '#9e9585',
          300: '#7a7060',
        },
        accent: {
          primary: '#5b4824',
          secondary: '#f7ce86',
          tertiary: '#e6ecd3',
          glow: 'rgba(247, 206, 134, 0.24)',
        },
        success: {
          DEFAULT: '#22c55e',
          dark: '#16a34a',
          glow: 'rgba(34, 197, 94, 0.15)',
        },
        warning: {
          DEFAULT: '#f59e0b',
          dark: '#d97706',
          glow: 'rgba(245, 158, 11, 0.15)',
        },
        danger: {
          DEFAULT: '#cb5150',
          dark: '#b91c1c',
          glow: 'rgba(203, 81, 80, 0.15)',
        },
        neutral: {
          100: '#fffbef',
          200: '#5f471d',
          300: '#7a6b4e',
          400: '#9e8b66',
          500: '#b5a382',
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 16px rgba(247, 206, 134, 0.25)',
        'glow-green': '0 0 16px rgba(34, 197, 94, 0.2)',
        'glow-orange': '0 0 16px rgba(245, 158, 11, 0.2)',
        'glow-red': '0 0 16px rgba(203, 81, 80, 0.2)',
        'card': '0 4px 16px rgba(91, 72, 36, 0.06)',
        'card-hover': '0 8px 28px rgba(91, 72, 36, 0.1)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(circle at center, var(--tw-gradient-stops))',
        'grid-pattern': 'linear-gradient(rgba(91, 72, 36, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(91, 72, 36, 0.04) 1px, transparent 1px)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2.2s ease-in-out infinite alternate',
        'shimmer': 'shimmer 1.5s infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 4px rgba(247, 206, 134, 0.2)' },
          '100%': { boxShadow: '0 0 16px rgba(247, 206, 134, 0.35)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      borderRadius: {
        'honey': '0.875rem',
      },
      fontFamily: {
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        'serif': ['Lora', 'Georgia', 'serif'],
        'mono': ['Space Grotesk', 'monospace'],
      },
    },
  },
  plugins: [],
}
