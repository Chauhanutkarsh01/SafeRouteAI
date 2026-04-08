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
        'dark-navy': '#0F172A',
        'roads': '#1E293B',
        'accent': '#F97316',
        'text-light': '#E2E8F0',
      }
    },
  },
  plugins: [],
}
