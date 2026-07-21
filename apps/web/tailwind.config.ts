import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        /* Opsora surface scale */
        s0: "#080b12",
        s1: "#0d1117",
        s2: "#161b22",
        s3: "#21262d",
        s4: "#30363d",
        /* Accent — warm amber/copper */
        accent: {
          DEFAULT: "#d4a053",
          dim: "rgba(212, 160, 83, 0.12)",
          glow: "rgba(212, 160, 83, 0.06)",
        },
        /* Semantic */
        ok: { DEFAULT: "#3fb950", dim: "rgba(63, 185, 80, 0.12)" },
        err: { DEFAULT: "#f85149", dim: "rgba(248, 81, 73, 0.12)" },
        warn: { DEFAULT: "#d29922", dim: "rgba(210, 153, 34, 0.12)" },
        info: { DEFAULT: "#58a6ff", dim: "rgba(88, 166, 255, 0.12)" },
        /* Text */
        t1: "#e6edf3",
        t2: "#8b949e",
        t3: "#484f58",
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Cascadia Code"', "ui-monospace", "monospace"],
        sans: ["Inter", "-apple-system", "system-ui", "sans-serif"],
      },
      animation: {
        "spin-slow": "spin 0.8s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
