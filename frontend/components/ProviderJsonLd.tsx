import { headers } from "next/headers";
import { getProviderHref } from "@/lib/provider-path";
import { getSiteUrl } from "@/lib/site";
import { normalizeExternalHttpUrl } from "@/lib/external-url";

export default async function ProviderJsonLd({
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
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": ["LocalBusiness", "MedicalOrganization"],
    name,
    url: `${getSiteUrl()}${getProviderHref({ slug })}`,
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
    ...(normalizeExternalHttpUrl(website) && { sameAs: normalizeExternalHttpUrl(website) }),
    ...(latitude && longitude && {
      geo: {
        "@type": "GeoCoordinates",
        latitude,
        longitude,
      },
    }),
    ...(rating && { description: `CQC rating: ${rating}` }),
  };

  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <script
      type="application/ld+json"
      nonce={nonce}
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
