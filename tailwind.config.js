/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./frontend/**/*.html", "./frontend/**/*.js"],
  theme: {
    extend: {
      colors: {
        brand: { 50:'#eef6ff',100:'#d9eaff',200:'#bcd8ff',300:'#8ebcff',400:'#5a99ff',500:'#2f74ff',600:'#1d5ae6',700:'#1745b8',800:'#183a92',900:'#183373' },
        ink: { 50:'#f7f8fa',100:'#eef0f4',200:'#d9dde5',300:'#b5bcc9',400:'#8a93a6',500:'#646d82',600:'#4a5266',700:'#363c4d',800:'#242938',900:'#161a26' },
      },
      fontFamily: { sans: ['Inter','ui-sans-serif','system-ui','sans-serif'] },
    },
  },
  plugins: [],
};
