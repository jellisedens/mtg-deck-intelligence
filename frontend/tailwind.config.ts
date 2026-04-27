import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Terminal-inspired dark palette
        bg: {
          primary: "#0a0a0f",
          secondary: "#12121a",
          tertiary: "#1a1a25",
          hover: "#22222f",
        },
        border: {
          DEFAULT: "#2a2a3a",
          focus: "#4a4a6a",
        },
        text: {
          primary: "#e0e0e8",
          secondary: "#8888a0",
          muted: "#55556a",
        },
        accent: {
          green: "#4ade80",
          red: "#f87171",
          blue: "#60a5fa",
          yellow: "#facc15",
          purple: "#c084fc",
        },
        // MTG mana colors
        mana: {
          white: "#f9f4e8",
          blue: "#0e68ab",
          black: "#3d3329",
          red: "#d3202a",
          green: "#00733e",
          colorless: "#9da1a4",
          multi: "#cfb53b",
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      },
      fontSize: {
        xxs: ["0.65rem", { lineHeight: "0.85rem" }],
      },
    },
  },
  plugins: [],
};
export default config;