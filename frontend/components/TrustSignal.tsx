export default function TrustSignal({ date }: { date?: string }) {
  const display = date
    ? `Last synced: ${new Date(date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`
    : "Daily refresh from the CQC public register";

  return (
    <p className="text-xs text-dusk text-center mt-2">
      Data sourced from CQC public register · {display}
    </p>
  );
}
