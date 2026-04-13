type SearchCriteria = {
  postcode?: string;
  q?: string;
  rating?: string;
  region?: string;
  service_type?: string;
  type?: string;
};

function hasValue(value?: string) {
  return typeof value === "string" && value.trim().length > 0;
}

export function hasSearchCriteria(criteria: SearchCriteria) {
  return Object.values(criteria).some(hasValue);
}
