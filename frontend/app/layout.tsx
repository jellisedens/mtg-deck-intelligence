import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { CardCacheProvider } from "@/lib/card-cache";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "MTG Deck Intelligence",
  description: "AI-powered Magic: The Gathering deck building and analytics",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <CardCacheProvider>
            <Nav />
            <main className="pt-12">{children}</main>
          </CardCacheProvider>
        </AuthProvider>
      </body>
    </html>
  );
}