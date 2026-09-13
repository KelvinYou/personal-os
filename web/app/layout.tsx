import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Personal OS Dashboard",
  description: "本地仪表盘（不部署）",
};

const NAV = [
  { href: "/", label: "Tracked Assets" },
  { href: "/eval-rollup", label: "Agent Signals" },
  { href: "/flows", label: "Flows" },
];

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
            __html: `try{var m=window.matchMedia('(prefers-color-scheme: dark)').matches;if(m)document.documentElement.classList.add('dark')}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-screen">
        <nav className="border-b">
          <div className="container flex max-w-5xl gap-4 py-3 text-sm">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-muted-foreground hover:text-foreground"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
