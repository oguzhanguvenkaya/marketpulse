/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      /* Colors are defined in @theme block in index.css (Tailwind v4 source of truth) */
      /* Only non-color tokens remain here */
      boxShadow: {
        'glow-gold': '0 0 16px rgba(247, 206, 134, 0.25)',
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
          '0%': { transform: 'translateX(-100%)' },
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
