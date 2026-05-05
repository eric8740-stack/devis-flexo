import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { cn } from "@/lib/utils";
import { FeedbackButton } from "@/components/feedback/FeedbackButton";
import { Header } from "@/components/Header";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/contexts/AuthContext";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "devis-flexo",
  description: "Application de devis pour TPE flexo étiquettes",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className={cn(geistSans.variable, geistMono.variable)}>
      <body className="font-sans antialiased">
        <AuthProvider>
          <Header />
          <ProtectedRoute>{children}</ProtectedRoute>
          <FeedbackButton />
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  );
}
