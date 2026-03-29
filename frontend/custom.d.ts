// Allow importing CSS files (e.g. leaflet/dist/leaflet.css) in TypeScript
declare module "*.css" {
  const content: string;
  export default content;
}
