/** @type {import('tailwindcss').Config}
 * Tokens ported 1:1 from the approved Claude Design system
 * (project: Smart Health Centre Management).
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F4F3EE",
        surface: "#FFFFFF",
        brand: {
          DEFAULT: "#0E6E58", // primary buttons, active states
          deep: "#0A3D33", // login + district headers
          darkest: "#0F2E27", // AI briefing panel
          success: "#1E8E5A",
        },
        ink: {
          DEFAULT: "#17241F",
          muted: "#5E6B64",
          faint: "#9AA39E",
        },
        ondark: {
          subtle: "#9CC3B9",
          soft: "#BFE3D8",
          softer: "#CFE3DD",
          bright: "#EAF4EF",
        },
        line: {
          DEFAULT: "#E4E1D8", // card border
          light: "#F0EEE7",
          lightest: "#F5F3ED",
          track: "#EFEDE5", // empty bar/track
          control: "#CBD3CF", // input/control border
        },
        status: {
          critical: "#B23A2E",
          "critical-soft": "#FBE7E3",
          warning: "#B9770F",
          "warning-soft": "#FBF0DC",
          "warning-deep": "#8A5A0C",
          healthy: "#1E8E5A",
          "healthy-soft": "#E4F1E9",
          "healthy-deep": "#146A45",
          underperforming: "#6D4AA6",
          "underperforming-soft": "#F0EAF7",
          "underperforming-deep": "#4A3A6B",
          info: "#2A6E8C", // bed-occupancy bar accent
        },
      },
      fontFamily: {
        sans: [
          '"IBM Plex Sans"',
          '"IBM Plex Sans Devanagari"',
          "system-ui",
          "sans-serif",
        ],
      },
      borderRadius: {
        pill: "22px",
        chip: "20px",
        role: "18px",
        card: "16px",
        tile: "14px",
        stepper: "12px",
        "stepper-sm": "11px",
        action: "10px",
        headerpill: "9px",
        seg: "7px",
        bar: "6px",
      },
      maxWidth: {
        district: "1180px",
        detail: "1000px",
        phone: "420px",
      },
    },
  },
  plugins: [],
};
