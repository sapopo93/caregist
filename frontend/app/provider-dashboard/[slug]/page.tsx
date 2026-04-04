"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function ProviderDashboardPage({ params }: { params: Promise<{ slug: string }> }) {
  const router = useRouter();
  const [slug, setSlug] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [provider, setProvider] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Form state
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState<string[]>([]);
  const [newPhotoUrl, setNewPhotoUrl] = useState("");
  const [virtualTourUrl, setVirtualTourUrl] = useState("");
  const [inspectionResponse, setInspectionResponse] = useState("");

  useEffect(() => {
    params.then(({ slug: s }) => {
      setSlug(s);
      const key = localStorage.getItem("caregist_api_key") || "";
      setApiKey(key);
      if (!key) {
        router.push("/login");
        return;
      }
      fetchProfile(s, key);
    });
  }, [params, router]);

  async function fetchProfile(s: string, key: string) {
    try {
      const res = await fetch(`/api/v1/providers/${s}/profile`, {
        headers: { "X-API-Key": key },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load profile.");
      }
      const data = await res.json();
      const p = data.data;
      setProvider(p);
      setDescription(p.profile_description || "");
      setPhotos(p.profile_photos ? (typeof p.profile_photos === "string" ? JSON.parse(p.profile_photos) : p.profile_photos) : []);
      setVirtualTourUrl(p.virtual_tour_url || "");
      setInspectionResponse(p.inspection_response || "");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/providers/${slug}/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({
          description: description || null,
          photos: photos.length > 0 ? photos : null,
          virtual_tour_url: virtualTourUrl || null,
          inspection_response: inspectionResponse || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to save.");
      }
      setSuccess("Profile updated successfully.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function addPhoto() {
    if (newPhotoUrl.trim() && !photos.includes(newPhotoUrl.trim())) {
      setPhotos([...photos, newPhotoUrl.trim()]);
      setNewPhotoUrl("");
    }
  }

  function removePhoto(index: number) {
    setPhotos(photos.filter((_, i) => i !== index));
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center text-dusk">
        Loading provider profile...
      </div>
    );
  }

  if (!provider) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <h1 className="text-2xl font-bold mb-4">Provider not found</h1>
        <p className="text-dusk mb-6">{error || "Could not load this provider."}</p>
        <Link href="/dashboard" className="text-clay underline">Back to dashboard</Link>
      </div>
    );
  }

  const tier = provider.profile_tier;
  const isClaimedByUser = provider.is_claimed;
  const tierConfig: Record<string, any> = {
    basic: { photos: 3, virtualTour: false, inspectionResponse: false, label: "Basic" },
    standard: { photos: 5, virtualTour: true, inspectionResponse: true, label: "Standard" },
    premium: { photos: 10, virtualTour: true, inspectionResponse: true, label: "Premium" },
  };
  const config = tierConfig[tier] || null;

  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold">Manage Listing</h1>
        <Link href={`/provider/${slug}`} className="text-sm text-clay underline">
          View public page
        </Link>
      </div>
      <p className="text-dusk mb-8">{provider.name}</p>

      {!isClaimedByUser && (
        <div className="bg-amber/10 border border-amber rounded-lg p-6 mb-6 text-center">
          <p className="font-semibold text-bark mb-2">This listing is not claimed</p>
          <p className="text-sm text-dusk mb-4">Claim this listing to edit your profile and respond to inspections.</p>
          <Link href={`/claim/${slug}`} className="px-6 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors">
            Claim this listing
          </Link>
        </div>
      )}

      {isClaimedByUser && !tier && (
        <>
          {/* Free inspection response editor */}
          <div className="bg-moss/5 border border-moss/20 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-bold mb-2 text-moss">Respond to Your Inspection — Free</h2>
            <p className="text-sm text-dusk mb-4">
              Tell families what you have done since your last CQC inspection. This appears publicly on your provider page.
            </p>
            <textarea
              value={inspectionResponse}
              onChange={(e) => setInspectionResponse(e.target.value)}
              maxLength={2000}
              rows={5}
              placeholder="We have invested in new staff training, upgraded our medication management systems, and appointed a new registered manager who brings 15 years of experience..."
              className="w-full px-4 py-3 rounded-lg border border-stone bg-white text-sm resize-y"
            />
            <p className="text-xs text-dusk mt-1">{inspectionResponse.length}/2,000 characters</p>
            <button
              onClick={handleSave}
              disabled={saving}
              className="mt-3 w-full py-3 bg-moss text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
            >
              {saving ? "Saving..." : "Publish Response"}
            </button>
            {error && <p className="text-alert text-xs mt-2">{error}</p>}
            {success && <p className="text-moss text-xs mt-2">{success}</p>}
          </div>

          {/* Upgrade upsell for other features */}
          <div className="bg-cream border border-stone rounded-lg p-6 mb-6 text-center">
            <p className="font-semibold text-bark mb-2">Want to add photos and a description?</p>
            <p className="text-sm text-dusk mb-4">
              Upgrade to an Enhanced Profile to add photos, a description, and a virtual tour link.
            </p>
            <div className="grid grid-cols-3 gap-4 max-w-lg mx-auto mb-4">
              <div className="bg-parchment rounded-lg p-3 text-center">
                <p className="font-bold text-bark">Basic</p>
                <p className="text-xl font-bold text-clay">£30<span className="text-xs text-dusk">/mo</span></p>
                <p className="text-xs text-dusk mt-1">3 photos + description</p>
              </div>
              <div className="bg-parchment rounded-lg p-3 text-center border-2 border-clay">
                <p className="font-bold text-bark">Standard</p>
                <p className="text-xl font-bold text-clay">£50<span className="text-xs text-dusk">/mo</span></p>
                <p className="text-xs text-dusk mt-1">5 photos + tour</p>
              </div>
              <div className="bg-parchment rounded-lg p-3 text-center">
                <p className="font-bold text-bark">Premium</p>
                <p className="text-xl font-bold text-clay">£80<span className="text-xs text-dusk">/mo</span></p>
                <p className="text-xs text-dusk mt-1">10 photos + everything</p>
              </div>
            </div>
            <a href="mailto:hello@caregist.co.uk" className="text-sm text-clay underline">
              Contact us to get started
            </a>
          </div>
        </>
      )}

      {isClaimedByUser && tier && config && (
        <>
          <div className="flex items-center gap-3 mb-6">
            <span className="px-3 py-1 rounded-full bg-moss text-white text-sm font-medium capitalize">
              {config.label} Profile
            </span>
            <span className="text-sm text-dusk">
              Up to {config.photos} photos
              {config.virtualTour && " + virtual tour"}
              {config.inspectionResponse && " + inspection response"}
            </span>
          </div>

          {error && (
            <div className="bg-alert/10 border border-alert/30 rounded-lg p-3 mb-4 text-sm text-alert">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-moss/10 border border-moss/30 rounded-lg p-3 mb-4 text-sm text-moss">
              {success}
            </div>
          )}

          {/* Description */}
          <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
            <h2 className="text-xl font-bold mb-3">About your service</h2>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={2000}
              rows={5}
              placeholder="Tell families about your care service. What makes you special? What should they expect?"
              className="w-full px-4 py-3 rounded-lg border border-stone bg-white text-sm resize-y"
            />
            <p className="text-xs text-dusk mt-1">{description.length}/2,000 characters</p>
          </div>

          {/* Photos */}
          <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
            <h2 className="text-xl font-bold mb-3">Photos</h2>
            {photos.length > 0 && (
              <div className="flex gap-3 flex-wrap mb-4">
                {photos.map((url, i) => (
                  <div key={i} className="relative">
                    <img src={url} alt={`Photo ${i + 1}`} className="h-24 w-24 object-cover rounded-lg" />
                    <button
                      onClick={() => removePhoto(i)}
                      className="absolute -top-2 -right-2 w-6 h-6 bg-alert text-white rounded-full text-xs font-bold"
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            )}
            {photos.length < config.photos && (
              <div className="flex gap-2">
                <input
                  type="url"
                  value={newPhotoUrl}
                  onChange={(e) => setNewPhotoUrl(e.target.value)}
                  placeholder="Paste image URL..."
                  className="flex-1 px-4 py-2 rounded-lg border border-stone bg-white text-sm"
                />
                <button
                  onClick={addPhoto}
                  className="px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors"
                >
                  Add
                </button>
              </div>
            )}
            <p className="text-xs text-dusk mt-2">{photos.length}/{config.photos} photos used</p>
          </div>

          {/* Virtual Tour */}
          {config.virtualTour && (
            <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
              <h2 className="text-xl font-bold mb-3">Virtual Tour</h2>
              <input
                type="url"
                value={virtualTourUrl}
                onChange={(e) => setVirtualTourUrl(e.target.value)}
                placeholder="Paste your virtual tour URL (e.g. Matterport, YouTube 360)..."
                className="w-full px-4 py-3 rounded-lg border border-stone bg-white text-sm"
              />
            </div>
          )}

          {/* Inspection Response */}
          {config.inspectionResponse && (
            <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
              <h2 className="text-xl font-bold mb-3">Response to Inspection</h2>
              <p className="text-sm text-dusk mb-3">
                Share your response to the latest CQC inspection. This appears publicly on your provider page.
              </p>
              <textarea
                value={inspectionResponse}
                onChange={(e) => setInspectionResponse(e.target.value)}
                maxLength={2000}
                rows={5}
                placeholder="We are pleased with our Good rating and continue to invest in..."
                className="w-full px-4 py-3 rounded-lg border border-stone bg-white text-sm resize-y"
              />
              <p className="text-xs text-dusk mt-1">{inspectionResponse.length}/2,000 characters</p>
            </div>
          )}

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </>
      )}
    </div>
  );
}
