/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./musicshowwins/**/*.{html,js}"],
  theme: {
    extend: {
      colors: {
        selection: "#ec4899",
      },
      screens: {
        "xs": "460px",
        "3xl": "1920px",
      },
      rotate: {
        '17': '17deg',
      }
    },
  },
  plugins: [],
};
