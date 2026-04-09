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
  // Provider-entered fields (claimed/paid profiles)
  logo_url: string | null;
  funding_types: string[] | null;
  fee_guidance: string | null;
  min_visit_duration: string | null;
  contract_types: string[] | null;
  age_ranges: string[] | null;
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

// ── Growth OS Config Types ──

export type GateKey = 'none' | 'email' | 'login' | 'paid' | 'manual';
export type ActionType = 'trial' | 'subscribe' | 'download' | 'save' | 'monitor' | 'apply' | 'claim';
export type Priority = 'now' | 'phase-2';
export type PageStatus = 'exists' | 'build';

export interface BuyerSegment {
  label: string;
  color: string;
  value: number;
}

export interface Gate {
  label: string;
  color: string;
}

export interface PricingVariant {
  name: string;
  price: string;
  features: string;
}

export interface PricingTier {
  tier: string;
  forWho: string;
  color: string;
  price: string;
  priceNote: string;
  recommended?: boolean;
  variants?: PricingVariant[];
  includes: string[];
  limit: string;
  pricingLogic: string;
}

export interface AddOn {
  name: string;
  price: string;
  note: string;
}

export interface LaunchPrice {
  tier: string;
  price: string;
  color: string;
}

export interface RevenueControl {
  tier: string;
  color: string;
  trigger: string;
  upgradeMoment: string;
  paywallMessage: string;
  targetConversion: string;
  targetARPU: string;
  primarySurface: string;
}

export interface UnitEconomic {
  surface: string;
  color: string;
  userType: string;
  acquisitionCost: string;
  conversionToPaid: string;
  strategicValue: string;
  expectedPayback: string;
}

export interface DefensibilityPoint {
  point: string;
  detail: string;
  color: string;
}

export interface SegmentStrategy {
  role: string;
  audience: string;
  insight: string;
  color: string;
}

export interface SeoPageFamily {
  family: string;
  urlPattern: string;
  estimatedPages: string;
  color: string;
  primaryKeywords: string[];
  structuredData: string;
  aeoBlock: string;
  freshnessSignal: string;
  distributionValue: string;
  conversionRole: string;
}

export interface AeoRule {
  rule: string;
  detail: string;
  applies: string;
  color: string;
}

export interface FlywheelSide {
  side: string;
  color: string;
  desc: string;
  pages: string[];
}

export interface CrmEvent {
  event: string;
  state: string;
  color: string;
}

export interface ExecutionScore {
  revenueImpact: number;
  buildComplexity: number;
  paybackSpeed: number;
  strategicCompounding: number;
}

export interface ClaimFlow {
  verification: string;
  claimantRoles: string;
  approvalSLA: string;
  freeTier: string;
  paidTier: string;
  postClaim: string;
  crmRecord: string;
}

export interface ToolSpec {
  inputs: string;
  outputs: string;
  freeLimit: string;
  aeoAngle: string;
  viralMechanic: string;
  distributionNote: string;
}

export interface PageSpec {
  id: number;
  status: PageStatus;
  priority: Priority;
  page: string;
  url: string;
  audience: string;
  buyerRank: number;
  jobToBeDone: string;
  currentGap: string;
  primaryCTA: string;
  actionType: ActionType;
  gate: GateKey;
  capturedAsset: string;
  revenuePath: string;
  upgradeTrigger: string;
  successMetric: string;
  followUpAutomation: string;
  trustLayer: string;
  crmOutcome: string;
  executionScore: ExecutionScore;
  claimFlow?: ClaimFlow;
  toolSpec?: ToolSpec;
}
