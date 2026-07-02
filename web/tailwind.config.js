/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // "clinical clarity" tokens — keep in sync with the approved Claude Design system
        paper: "#F6F8F8",
        ink: "#16302E",
        teal: {
          DEFAULT: "#0E6E63",
          dark: "#0A5249",
          deep: "#123B36", // deep header ground from the design
        },
        status: {
          critical: "#C43D3D",
          warning: "#B07C1F",
          healthy: "#2E7D46",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '"IBM Plex Sans Devanagari"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
