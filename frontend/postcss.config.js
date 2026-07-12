export default {
  plugins: {
    // Tailwind v4's PostCSS plugin handles vendor prefixing via Lightning CSS,
    // so a separate autoprefixer pass is redundant.
    '@tailwindcss/postcss': {},
  },
}
