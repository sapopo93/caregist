export const DEFAULT_REGION_OPTIONS = [
  "East",
  "East Midlands",
  "London",
  "North East",
  "North West",
  "South East",
  "South West",
  "West Midlands",
  "Yorkshire & Humberside",
];

export const DEFAULT_SERVICE_TYPE_OPTIONS = [
  "Clinic",
  "Dentist",
  "Doctors/Gps",
  "Homecare Agencies",
  "Hospice",
  "Hospitals - Mental Health/Capacity",
  "Nursing Homes",
  "Residential Homes",
  "Supported Living",
];

export const DEFAULT_RATING_OPTIONS = [
  "Outstanding",
  "Good",
  "Requires improvement",
  "Inadequate",
  "Inspected But Not Rated",
  "No Published Rating",
  "Not Yet Inspected",
];

export const DIRECTORY_OPPORTUNITY_OPTIONS = [
  {
    value: "new_90",
    label: "Registered in last 90 days",
    shortLabel: "New registrations",
    audience: "Suppliers, software, recruiters, equipment and policy providers",
  },
  {
    value: "inadequate",
    label: "Currently rated Inadequate",
    shortLabel: "Inadequate providers",
    audience: "Turnaround consultants and quality specialists",
  },
  {
    value: "requires_improvement",
    label: "Currently Requires Improvement",
    shortLabel: "Requires Improvement",
    audience: "Consultants, compliance teams and improvement partners",
  },
  {
    value: "not_yet_inspected",
    label: "Not yet inspected",
    shortLabel: "Not yet inspected",
    audience: "Suppliers targeting early-stage provider setup",
  },
  {
    value: "stale_inspection",
    label: "Inspection older than 3 years",
    shortLabel: "Stale inspections",
    audience: "Analysts and monitoring teams looking for overdue movement",
  },
] as const;

export type DirectoryOpportunity = (typeof DIRECTORY_OPPORTUNITY_OPTIONS)[number]["value"];

export function isDirectoryOpportunity(value: string): value is DirectoryOpportunity {
  return DIRECTORY_OPPORTUNITY_OPTIONS.some((option) => option.value === value);
}

export function getDirectoryOpportunity(value: string) {
  return DIRECTORY_OPPORTUNITY_OPTIONS.find((option) => option.value === value) ?? null;
}
