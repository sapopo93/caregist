import { staticFile } from "remotion";

// Brand tokens, matching frontend/app/globals.css.
export const C = {
  clay: "#C1784F",
  bark: "#6B4C35",
  parchment: "#F5EFE4",
  moss: "#4A5E45",
  dusk: "#655B4E",
  stone: "#D6CFC4",
  cream: "#FDFAF5",
  charcoal: "#2B2520",
  amber: "#D4943A",
  sage: "#7E9B79",
  cta: "#0A7A57",
};

export const SERIF = "'Playfair Display', Georgia, serif";
export const SANS = "'DM Sans', system-ui, sans-serif";

export const fontFaces = `
@font-face { font-family: 'Playfair Display'; src: url('${staticFile("fonts/playfair-display-latin-wght-normal.woff2")}') format('woff2'); font-weight: 700 800; }
@font-face { font-family: 'DM Sans'; src: url('${staticFile("fonts/dm-sans-latin-wght-normal.woff2")}') format('woff2'); font-weight: 300 600; }
`;
