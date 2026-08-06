export type FeedCapabilities = {
  feed: boolean;
  savedFilters: boolean;
  digest: boolean;
  export: boolean;
};

const NO_FEED: FeedCapabilities = {
  feed: false,
  savedFilters: false,
  digest: false,
  export: false,
};

const TIER_FEED_CAPABILITIES: Record<string, FeedCapabilities> = {
  free: { feed: true, savedFilters: false, digest: false, export: false },
  "alerts-pro": NO_FEED,
  starter: { feed: true, savedFilters: true, digest: true, export: true },
  pro: { feed: true, savedFilters: true, digest: true, export: true },
  business: { feed: true, savedFilters: true, digest: true, export: true },
  enterprise: { feed: true, savedFilters: true, digest: true, export: true },
};

export function feedCapabilitiesForTier(tier: string): FeedCapabilities {
  return TIER_FEED_CAPABILITIES[tier] ?? NO_FEED;
}
