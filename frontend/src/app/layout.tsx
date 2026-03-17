import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import { Inter } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";
import Navbar from "@/components/Navbar";
import AuthProvider from "@/components/AuthProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";

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
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/"
      signUpFallbackRedirectUrl="/"
      appearance={{
        baseTheme: dark,
        variables: {
          colorPrimary: "#1DB954",
          colorBackground: "#181818",
          colorInputBackground: "#282828",
          colorInputText: "#ffffff",
          colorText: "#ffffff",
          colorTextSecondary: "#b3b3b3",
          colorNeutral: "#ffffff",
          colorTextOnPrimaryBackground: "#000000",
        },
        elements: {
          card: "!bg-[#181818] border border-[#282828] shadow-2xl rounded-2xl",
          formButtonPrimary: "bg-[#1DB954] hover:bg-[#1ed760] text-black font-bold rounded-full",
          formFieldInput: "bg-[#282828] border-[#282828] text-white rounded-md",
          formFieldLabel: "text-[#b3b3b3]",
          footerActionLink: "text-[#1DB954] hover:text-[#1ed760]",
          socialButtonsBlockButton:
            "bg-[#282828] border-[#383838] hover:bg-[#333] text-white",
          socialButtonsBlockButtonText: "text-white font-medium",
          socialButtonsProviderIcon__x: "brightness-0 invert",
          socialButtonsProviderIcon__apple: "brightness-0 invert",
          socialButtonsProviderIcon__github: "brightness-0 invert",
          userButtonPopoverCard: "bg-[#181818] border border-[#282828]",
          userButtonPopoverActionButton: "text-white hover:bg-[#282828]",
          userButtonPopoverActionButtonText: "text-white",
          userButtonPopoverActionButtonIcon: "text-[#b3b3b3]",
          userButtonPopoverFooter: "border-t border-[#282828]",
          userPreviewMainIdentifier: "text-white",
          userPreviewSecondaryIdentifier: "text-[#b3b3b3]",
        },
      }}
    >
      <html lang="en" className={inter.variable}>
        <body className="min-h-screen bg-black text-white antialiased font-sans selection:bg-[#1DB954]/30 selection:text-white">
          <TooltipProvider>
            <Navbar />
            <AuthProvider>
              <ErrorBoundary>
                <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                  {children}
                </main>
              </ErrorBoundary>
            </AuthProvider>
          </TooltipProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
