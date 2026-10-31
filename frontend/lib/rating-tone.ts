/** Background utility class for a published CQC overall rating; neutral when unpublished. */
export function ratingToneClass(rating: string | null | undefined): string {
  switch ((rating ?? "").trim().toLowerCase()) {
    case "outstanding":
      return "bg-moss";
    case "good":
      return "bg-sage";
    case "requires improvement":
      return "bg-amber";
    case "inadequate":
      return "bg-alert";
    default:
      return "bg-stone";
  }
}
