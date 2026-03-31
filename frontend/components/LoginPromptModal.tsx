"use client";

import Link from "next/link";

export default function LoginPromptModal({
  action,
  onClose,
}: {
  action: string;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-lg p-6 max-w-sm mx-4 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-bark mb-2">Sign in to {action}</h3>
        <p className="text-sm text-dusk mb-5">
          Create a free account or log in to continue.
        </p>
        <div className="flex gap-3 justify-center">
          <Link
            href="/signup"
            className="px-5 py-2.5 bg-clay text-white rounded-lg text-sm font-medium hover:bg-bark transition-colors"
          >
            Sign Up Free
          </Link>
          <Link
            href="/login"
            className="px-5 py-2.5 border border-clay text-clay rounded-lg text-sm font-medium hover:bg-clay hover:text-white transition-colors"
          >
            Log In
          </Link>
        </div>
        <button onClick={onClose} className="mt-4 text-xs text-dusk hover:text-bark">
          Cancel
        </button>
      </div>
    </div>
  );
}
