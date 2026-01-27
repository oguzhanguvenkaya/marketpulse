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
          900: '#1e1e1e',
          800: '#2a2a2a',
          700: '#3a3a3a',
          600: '#4a4a4a',
          500: '#5a5a5a',
          400: '#6a6a6a',
          300: '#767676',
        },
        accent: {
          primary: '#00d4ff',
          secondary: '#0099cc',
          tertiary: '#006699',
          glow: 'rgba(0, 212, 255, 0.15)',
        },
        success: {
          DEFAULT: '#00e676',
          dark: '#00c853',
          glow: 'rgba(0, 230, 118, 0.15)',
        },
        warning: {
          DEFAULT: '#ffab00',
          dark: '#ff8f00',
          glow: 'rgba(255, 171, 0, 0.15)',
        },
        danger: {
          DEFAULT: '#ff5252',
          dark: '#ff1744',
          glow: 'rgba(255, 82, 82, 0.15)',
        },
        neutral: {
          100: '#f5f5f5',
          200: '#e0e0e0',
          300: '#b0b0b0',
          400: '#808080',
          500: '#606060',
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(0, 212, 255, 0.3)',
        'glow-green': '0 0 20px rgba(0, 230, 118, 0.3)',
        'glow-orange': '0 0 20px rgba(255, 171, 0, 0.3)',
        'glow-red': '0 0 20px rgba(255, 82, 82, 0.3)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 8px 32px rgba(0, 0, 0, 0.5)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
        'grid-pattern': 'linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(0, 212, 255, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 212, 255, 0.4)' },
        },
      },
    },
  },
  plugins: [],
}
