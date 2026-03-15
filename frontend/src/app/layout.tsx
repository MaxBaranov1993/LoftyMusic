import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Inter } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";
import Navbar from "@/components/Navbar";
import AuthProvider from "@/components/AuthProvider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Lofty — AI Music Generation",
  description: "Generate music from text prompts using AI",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "#4FB7B3",
          colorBackground: "#FFFFFF",
          colorInputBackground: "#F8FFFE",
          colorInputText: "#31326F",
          colorText: "#31326F",
        },
      }}
    >
      <html lang="en" className={inter.variable}>
        <body className="min-h-screen bg-background text-foreground antialiased font-sans">
          <TooltipProvider>
            <Navbar />
            <AuthProvider>
              <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {children}
              </main>
            </AuthProvider>
          </TooltipProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
