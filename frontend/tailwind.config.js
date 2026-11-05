/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Sampled from Nettle's logo.
        brand: { DEFAULT: "#f4530f", dark: "#d4440a" },
        cream: { DEFAULT: "#fff5e9", light: "#fdfaf5" },
      },
    },
  },
  plugins: [],
};
