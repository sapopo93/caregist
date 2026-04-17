import type { Metadata } from "next";
import StoryVideoPlayer from "@/components/StoryVideoPlayer";

export const metadata: Metadata = {
  title: "The House That Worked Together | Animated Story",
  description:
    "A five-minute animated story experience for children about kindness, peace, and working together.",
};

export default function StoryVideoPage() {
  return <StoryVideoPlayer />;
}
