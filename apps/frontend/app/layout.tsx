import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RAG Corp",
  description: "Busqueda semantica y respuestas basadas en documentos.",
};

/**
 * Name: RootLayout (app/layout)
 *
 * Responsibilities:
 * - Provide the global HTML and BODY wrapper for the App Router tree
 * - Apply global typography by wiring Geist font variables
 * - Ensure global styles are loaded via globals.css
 * - Expose metadata used by Next.js for title/description
 * - Establish the default theme class for the document root
 *
 * Collaborators:
 * - next/metadata types for compile-time metadata shape
 * - next/font/google for Geist and Geist_Mono configuration
 * - globals.css for base reset and app-wide styles
 * - React children passed by the App Router
 *
 * Notes/Constraints:
 * - Must remain a server component (no "use client") for Next.js layouts
 * - The className wiring must stay stable to avoid style regressions
 * - Only structural markup belongs here; no feature logic or data fetching
 * - The HTML lang attribute should reflect the product language choice
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
