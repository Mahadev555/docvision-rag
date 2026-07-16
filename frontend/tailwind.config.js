/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        base: {
          950: "#0a0a0f",
          900: "#121218",
          850: "#181820",
          800: "#1e1e28",
          700: "#2a2a38",
          600: "#3a3a4a",
        },
        accent: {
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
        },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(139,92,246,0.15), 0 8px 24px -4px rgba(139,92,246,0.25)",
      },
    },
  },
  plugins: [],
};
