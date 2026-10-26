import { ChatShell } from "@/components/chat/chat-shell";
import { isAccessRequired } from "@/lib/access-session.mjs";

export const dynamic = "force-dynamic";

export default function Home() {
  return <ChatShell showLogout={isAccessRequired()} />;
}
