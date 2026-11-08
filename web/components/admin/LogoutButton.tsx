"use client";

import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LogoutButton() {
  const router = useRouter();
  return (
    <button
      className="mt-2 block font-semibold text-slate-700 underline"
      onClick={async () => {
        await api("/api/auth/logout", { method: "POST" });
        router.replace("/login");
      }}
    >
      Log out
    </button>
  );
}
