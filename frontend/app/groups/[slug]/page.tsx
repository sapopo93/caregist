import { permanentRedirect } from "next/navigation";

export default function DeferredGroupPage() {
  permanentRedirect("/search");
}
