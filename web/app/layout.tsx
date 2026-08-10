import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tracked Assets — Personal OS",
  description: "本地理财仪表盘（不部署）",
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
            __html: `try{var m=window.matchMedia('(prefers-color-scheme: dark)').matches;if(m)document.documentElement.classList.add('dark')}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
