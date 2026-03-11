/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'accent-color': 'rgb(var(--accent-color-rgb) / <alpha-value>)',
        'accent-color-rgb': 'var(--accent-color-rgb)',
        // Modern Desaturated Palette (Standard)
        'modern': {
          'bg-light': '#F8F9FA',
          'bg-dark': '#121212',
          'text-light': '#212529',
          'text-dark': '#E9ECEF',
          'accent': '#495057'
        },
        // High Contrast Palette (+)
        'plus': {
          'bg-light': '#FFFFFF',
          'bg-dark': '#000000',
          'primary': '#0D6EFD',
          'secondary': '#6610F2',
          'accent': '#FFC107'
        }
      }
    },
  },
  plugins: [],
}
