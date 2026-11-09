import type { Metadata } from "next";
import { PostsPage } from "@/components/office/posts-page";
import "../office/office.css";

export const metadata: Metadata = { title: "Posts · Personal OS", description: "Final post carousels and publication copy from the private post collection." };
export const dynamic = "force-dynamic";
// Moved out of the office (docs/design/office-attention-radar.md §8); same local-only API.
export default function Page() { return <PostsPage />; }
