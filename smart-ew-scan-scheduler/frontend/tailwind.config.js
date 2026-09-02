/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#0f172a",
        panelLight: "#1e293b",
        accent: "#22d3ee",
        hit: "#4ade80",
        miss: "#f87171",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
