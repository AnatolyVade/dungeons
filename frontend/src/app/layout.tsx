import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Realms of Fate",
  description: "AI-powered D&D open world adventure",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        {children}
      </body>
    </html>
  );
}
