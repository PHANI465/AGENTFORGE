/** @type {import('postcss-load-config').Config} */
// Empty on purpose: Tailwind v4 is wired in via @tailwindcss/vite (vite.config.ts),
// which handles CSS processing directly and needs no PostCSS plugins. This file
// exists only to shadow an unrelated postcss.config.mjs one directory up the
// tree (E:\PHANI\) that Vite's PostCSS resolution otherwise picks up.
const config = {
  plugins: {},
}

export default config
