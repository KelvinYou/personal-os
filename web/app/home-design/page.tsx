import type { Metadata } from "next";
import { HomePreview } from "@/components/home-design/home-preview";

export const metadata: Metadata = {
  title: "Home design · Personal OS",
  description: "Explore a mid-century minimal home in a local 3D viewer with an indoor walk mode.",
};

// Pattern: detail. Reuse: dashboard navigation, appearance tokens, DataState.
// New: a same-origin 3D viewer; the model is owned locally under web/components/home-design/.
export default function HomeDesignPage() {
  return (
    <main id="main-content" className="container max-w-7xl space-y-6 px-4 py-8 md:px-6">
      <header>
        <p className="eyebrow">Living spaces</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">Home design</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
          Explore a mid-century minimal interior in dollhouse view, or enter and walk through each room.
          Use WASD or arrow keys to move, drag to look around, and press Escape to return.
          The model follows the floor plan approximately; confirm dimensions on site before buying furniture.
        </p>
      </header>
      <HomePreview />
    </main>
  );
}
