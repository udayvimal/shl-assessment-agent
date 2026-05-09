import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        shl: {
          blue: "#003087",
          teal: "#00B5B1",
          light: "#F0F4FF",
        },
      },
    },
  },
  plugins: [],
};
export default config;
