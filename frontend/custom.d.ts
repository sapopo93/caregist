// Allow the dynamic `import("leaflet/dist/leaflet.css")` in components/MapView.tsx.
// Scoped to this exact specifier (not a "*.css" wildcard) so it can't shadow
// Next's own "*.module.css" typing (next/types/global.d.ts), which CSS Modules
// need for their class-name lookup object.
declare module "leaflet/dist/leaflet.css" {
  const content: string;
  export default content;
}
