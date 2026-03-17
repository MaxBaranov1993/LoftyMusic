import { SignUp } from "@clerk/nextjs";
import { Music2 } from "lucide-react";
import Link from "next/link";

export default function SignUpPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] space-y-8">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5 group">
        <div className="w-10 h-10 rounded-full bg-[#1DB954] flex items-center justify-center transition-all duration-200 group-hover:scale-105">
          <Music2 className="w-5 h-5 text-black" />
        </div>
        <span className="text-2xl font-bold tracking-tight text-foreground">
          Lofty
        </span>
      </Link>

      {/* Clerk Sign-Up */}
      <SignUp
        appearance={{
          elements: {
            rootBox: "w-full max-w-md",
            card: "bg-[#181818] border border-[#282828] shadow-2xl rounded-2xl w-full",
            socialButtonsBlockButton:
              "bg-[#282828] border-[#383838] hover:bg-[#333] text-white",
            socialButtonsBlockButtonText: "text-white font-medium",
            socialButtonsBlockButtonArrow: "text-white",
            socialButtonsProviderIcon__x: "brightness-0 invert",
            socialButtonsProviderIcon__apple: "brightness-0 invert",
          },
        }}
      />
    </div>
  );
}
