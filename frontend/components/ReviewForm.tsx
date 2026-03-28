"use client";

import { useState } from "react";
import { submitReview } from "@/lib/actions";
import StarRating from "./StarRating";

export default function ReviewForm({ slug }: { slug: string }) {
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [relationship, setRelationship] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === 0) return;
    setSubmitting(true);
    setResult(null);

    const res = await submitReview(slug, {
      rating,
      title,
      body,
      reviewer_name: name,
      reviewer_email: email,
      relationship: relationship || undefined,
    });

    setSubmitting(false);
    if (res.error) {
      setResult({ ok: false, message: res.error });
    } else {
      setResult({ ok: true, message: "Thank you for your review. It will appear once moderated." });
      setRating(0);
      setTitle("");
      setBody("");
      setName("");
      setEmail("");
      setRelationship("");
    }
  }

  if (result?.ok) {
    return (
      <div className="bg-moss/10 border border-moss/30 rounded-lg p-4 text-moss">
        <p className="font-medium">{result.message}</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-bark mb-1">Your rating</label>
        <StarRating rating={rating} interactive onChange={setRating} size="lg" />
        {rating === 0 && result?.ok === false && (
          <p className="text-alert text-sm mt-1">Please select a rating</p>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="review-name" className="block text-sm font-medium text-bark mb-1">Your name</label>
          <input id="review-name" type="text" required maxLength={100} value={name} onChange={(e) => setName(e.target.value)}
            className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
        </div>
        <div>
          <label htmlFor="review-email" className="block text-sm font-medium text-bark mb-1">Email <span className="text-dusk font-normal">(not published)</span></label>
          <input id="review-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
        </div>
      </div>

      <div>
        <label htmlFor="review-relationship" className="block text-sm font-medium text-bark mb-1">Your connection</label>
        <select id="review-relationship" value={relationship} onChange={(e) => setRelationship(e.target.value)}
          className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50 bg-white">
          <option value="">Select (optional)</option>
          <option value="family_member">Family Member</option>
          <option value="service_user">Service User</option>
          <option value="professional">Professional</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div>
        <label htmlFor="review-title" className="block text-sm font-medium text-bark mb-1">Review title</label>
        <input id="review-title" type="text" required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)}
          placeholder="Summarise your experience"
          className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
      </div>

      <div>
        <label htmlFor="review-body" className="block text-sm font-medium text-bark mb-1">Your review</label>
        <textarea id="review-body" required maxLength={5000} rows={4} value={body} onChange={(e) => setBody(e.target.value)}
          placeholder="What was your experience with this provider?"
          className="w-full border border-stone rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-clay/50" />
      </div>

      {result && !result.ok && (
        <p className="text-alert text-sm">{result.message}</p>
      )}

      <button type="submit" disabled={submitting || rating === 0}
        className="px-6 py-2.5 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
        {submitting ? "Submitting..." : "Submit Review"}
      </button>
    </form>
  );
}
