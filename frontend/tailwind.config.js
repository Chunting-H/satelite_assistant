/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#1a56db",
        secondary: "#0694a2",
        accent: "#7e3af2",
        danger: "#e02424",
        success: "#0e9f6e",
      },
    },
  },
  plugins: [],
}