/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#090d14",
        surface: "#0f1420",
        surfaceHover: "#161d2e",
        surfaceRaised: "#131927",
        borderMuted: "#1e2638",
        borderSubtle: "#28334a",
        textPrimary: "#f0f4f8",
        textSecondary: "#8b9bb4",
        textMuted: "#56657f",
        accent: "#38bdf8",
        accentMuted: "#0284c7",
        success: "#34d399",
        warning: "#fbbf24",
        danger: "#f87171",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "SF Mono",
          "Consolas",
          "Liberation Mono",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};


