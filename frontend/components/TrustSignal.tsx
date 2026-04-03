export default function TrustSignal({ date }: { date?: string }) {
  const display = date
    ? new Date(date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
    : "weekly";

  return (
    <p className="text-xs text-dusk text-center mt-2">
      Data sourced from CQC public register · Updated daily · Last synced: {display}
    </p>
  );
}
