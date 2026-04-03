"use client";

export default function PrintButton() {
  return (
    <button
      onClick={() => window.print()}
      className="text-sm text-clay underline hover:text-bark print:hidden"
    >
      Print
    </button>
  );
}
