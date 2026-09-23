# Self-hosted fonts

These variable, latin-subset `.woff2` files are vendored from OFL-licensed
npm packages so `next build` needs no network access to `fonts.gstatic.com` /
`fonts.googleapis.com`. They were extracted with `npm pack <pkg>@<version>`
(not `npm install` — they are not a runtime dependency) and are not modified.

| File | Package | Version |
|------|---------|---------|
| `dm-sans-latin-wght-normal.woff2` | `@fontsource-variable/dm-sans` | 5.3.0 |
| `playfair-display-latin-wght-normal.woff2` | `@fontsource-variable/playfair-display` | 5.3.0 |
| `inter-latin-wght-normal.woff2` | `@fontsource-variable/inter` | 5.3.0 |
| `source-serif-4-latin-wght-normal.woff2` | `@fontsource-variable/source-serif-4` | 5.3.0 |

Each file's licence is the matching `OFL-<family>.txt` (SIL Open Font
License 1.1), copied verbatim from the source package.

Loaded via `next/font/local` in `app/layout.tsx` (DM Sans, Playfair Display,
sitewide) and `app/pricing/territory/page.tsx` (Source Serif 4, Inter, scoped
to that route). See `frontend/lib/no-remote-fonts.test.ts` for the regression
guard against reintroducing `next/font/google`.
