import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IKSHA AI - Enterprise Hiring Intelligence",
  description: "Next-generation hiring pipeline with deep reasoning and identity trust verification.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className="antialiased selection:bg-indigo-500/30">
        {children}
      </body>
    </html>
  );
}
