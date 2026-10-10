import type { Metadata } from "next";
import { DashboardNav } from "@/components/dashboard-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Personal OS Dashboard",
  description: "本地仪表盘（不部署）",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        {/* Resolve the theme before first paint so dark mode never flashes. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('os-theme');var d=t?t==='dark':matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',d);document.documentElement.dataset.material=localStorage.getItem('os-material')||'glass'}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-screen">
        <a className="skip-link" href="#main-content">Skip to content</a>
        <DashboardNav />
        {children}
      </body>
    </html>
  );
}
