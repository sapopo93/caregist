export default function ProviderJsonLd({
  name,
  type,
  address,
  town,
  postcode,
  region,
  phone,
  website,
  rating,
  latitude,
  longitude,
  slug,
}: {
  name: string;
  type?: string | null;
  address?: string | null;
  town?: string | null;
  postcode?: string | null;
  region?: string | null;
  phone?: string | null;
  website?: string | null;
  rating?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  slug: string;
}) {
  const ratingMap: Record<string, number> = {
    Outstanding: 5,
    Good: 4,
    "Requires Improvement": 2,
    Inadequate: 1,
  };

  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": ["LocalBusiness", "MedicalOrganization"],
    name,
    url: `https://caregist.co.uk/provider/${slug}`,
    ...(type && { additionalType: type }),
    address: {
      "@type": "PostalAddress",
      ...(address && { streetAddress: address }),
      ...(town && { addressLocality: town }),
      ...(region && { addressRegion: region }),
      ...(postcode && { postalCode: postcode }),
      addressCountry: "GB",
    },
    ...(phone && { telephone: phone }),
    ...(website && { sameAs: website }),
    ...(latitude && longitude && {
      geo: {
        "@type": "GeoCoordinates",
        latitude,
        longitude,
      },
    }),
    ...(rating && ratingMap[rating] && {
      aggregateRating: {
        "@type": "AggregateRating",
        ratingValue: ratingMap[rating],
        bestRating: 5,
        worstRating: 1,
        ratingCount: 1,
        reviewCount: 1,
      },
    }),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
