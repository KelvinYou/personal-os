import { redirect } from "next/navigation";
import { legacyWorldRedirect } from "@/lib/office-departments";

export const dynamic = "force-dynamic";

// The street and its doors were replaced by one flat town on /office
// (docs/design/office-world.md). Old links land on the matching department.
export default async function WorldPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  redirect(legacyWorldRedirect(await searchParams));
}
