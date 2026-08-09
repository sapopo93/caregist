import { permanentRedirect } from "next/navigation";

export default function DeferredGroupsPage() {
  permanentRedirect("/search");
}
