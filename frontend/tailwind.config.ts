import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "hsl(var(--bg) / <alpha-value>)",
          soft: "hsl(var(--bg-soft) / <alpha-value>)"
        },
        fg: {
          DEFAULT: "hsl(var(--fg) / <alpha-value>)",
          muted: "hsl(var(--fg-muted) / <alpha-value>)"
        },
        card: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          border: "hsl(var(--card-border) / <alpha-value>)"
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          soft: "hsl(var(--accent) / 0.12)"
        },
        good: "hsl(var(--good) / <alpha-value>)",
        warn: "hsl(var(--warn) / <alpha-value>)",
        bad: "hsl(var(--bad) / <alpha-value>)"
      },
      boxShadow: {
        glow: "0 0 0 1px hsl(var(--card-border) / 1), 0 10px 30px -12px rgba(0,0,0,0.35)",
        glowLg: "0 0 0 1px hsl(var(--card-border) / 1), 0 18px 60px -20px rgba(0,0,0,0.45)"
      }
    }
  },
  plugins: []
} satisfies Config;


