import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { default: "Admin", template: "%s · Crayonlark Admin" },
  robots: { index: false, follow: false },
};

// Apply the saved light/dark choice before paint (no flash). Default follows the OS setting.
const THEME_SCRIPT = `try{var t=localStorage.getItem("cl-admin-theme");if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))document.documentElement.classList.add("dark")}catch(e){}`;

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="admin min-h-dvh bg-slate-50 font-sans text-ink">
      <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      {children}
    </div>
  );
}
