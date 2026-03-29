export interface Provider {
  id: string;
  name: string;
  slug: string;
  type: string | null;
  status: string | null;
  town: string | null;
  postcode: string | null;
  region: string | null;
  overall_rating: string | null;
  service_types: string | null;
  quality_tier: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  latitude: number | null;
  longitude: number | null;
  county: string | null;
  local_authority: string | null;
  specialisms: string | null;
  regulated_activities: string | null;
  number_of_beds: number | null;
  ownership_type: string | null;
  quality_score: number | null;
  rating_safe: string | null;
  rating_effective: string | null;
  rating_caring: string | null;
  rating_responsive: string | null;
  rating_well_led: string | null;
  last_inspection_date: string | null;
  inspection_report_url: string | null;
  is_claimed: boolean;
  review_count: number;
  avg_review_rating: number | null;
}

export interface SearchMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface SearchResults {
  data: Provider[];
  meta: SearchMeta;
}

export interface Review {
  id: number;
  rating: number;
  title: string;
  body: string;
  reviewer_name: string;
  relationship: string | null;
  visit_date: string | null;
  created_at: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
}
