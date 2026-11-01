import type { Metadata } from "next";
import { UsageDashboard } from "@/components/usage/usage-dashboard";
import { isAccessRequired } from "@/lib/access-session.mjs";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Usage | VibeCraft",
  description: "Ringkasan GPU dan audit aktivitas generate VibeCraft.",
};

export default function UsagePage() {
  return <UsageDashboard showLogout={isAccessRequired()} />;
}
