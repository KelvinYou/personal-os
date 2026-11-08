import type { Metadata } from "next";
import { CollaborationWorkspace } from "@/components/office-collaboration/workspace";

export const metadata: Metadata = { title: "Office collaboration · Personal OS" };
export default function CollaborationPage() {
  return <main id="main-content" className="container max-w-7xl space-y-8 px-4 py-8 md:px-6 md:py-12">
    <header className="space-y-3">
      <p className="eyebrow">Virtual office / Collaboration</p>
      <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">Work together, with clear ownership.</h1>
      <p className="max-w-3xl text-sm leading-6 text-muted-foreground">Claim work, hand off evidence and reserve shared resources. Managed teams use fresh read-only Codex threads; your existing sessions keep working.</p>
      <a className="inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4" href="/office">Back to the 3D office →</a>
    </header>
    <CollaborationWorkspace />
  </main>;
}
