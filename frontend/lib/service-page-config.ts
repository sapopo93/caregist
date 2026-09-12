export const SERVICE_PAGES = {
  "care-homes": {
    serviceType: "residential-care-homes",
    displayName: "Care Homes",
  },
  "nursing-homes": {
    serviceType: "nursing-care-homes",
    displayName: "Nursing Homes",
  },
  "home-care": {
    serviceType: "home-care",
    displayName: "Home Care Agencies",
  },
  "gp-surgeries": {
    serviceType: "primary-medical-care",
    displayName: "GP Surgeries",
  },
  dental: {
    serviceType: "dental-services",
    displayName: "Dental Practices",
  },
  "supported-living": {
    serviceType: "supported-living",
    displayName: "Supported Living",
  },
} as const;

export function getServicePage(slug: string) {
  if (!Object.hasOwn(SERVICE_PAGES, slug)) return null;
  return SERVICE_PAGES[slug as keyof typeof SERVICE_PAGES];
}

export function getServicePageSlugs(): string[] {
  return Object.keys(SERVICE_PAGES);
}
