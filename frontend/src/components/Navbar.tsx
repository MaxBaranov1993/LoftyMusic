"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth, UserButton } from "@clerk/nextjs";
import { Music2, Settings, Wand2, FileCode2, Server } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Generate" },
  { href: "/tracks", label: "My Tracks" },
  { href: "/fine-tune", label: "Fine-Tune" },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/api-docs", label: "API", icon: FileCode2 },
  { href: "/gpu-farm", label: "GPU Farm", icon: Server },
];

export default function Navbar() {
  const pathname = usePathname();
  const { isSignedIn } = useAuth();

  return (
    <nav className="sticky top-0 z-50 bg-black/90 backdrop-blur-lg">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-full bg-[#1DB954] flex items-center justify-center transition-all duration-200 group-hover:scale-105">
            <Music2 className="w-5 h-5 text-black" />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">
            Lofty
          </span>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-2">
          {isSignedIn ? (
            <>
              {/* Nav links */}
              <div className="flex items-center gap-1 mr-2">
                {NAV_ITEMS.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <Link key={item.href} href={item.href}>
                      <Button
                        variant={isActive ? "default" : "ghost"}
                        size="sm"
                        className={cn(
                          "text-sm font-bold rounded-full transition-all duration-200",
                          isActive
                            ? "bg-white text-black hover:bg-white hover:scale-100"
                            : "text-[#B3B3B3] hover:text-white hover:bg-transparent hover:scale-105"
                        )}
                      >
                        {item.label}
                      </Button>
                    </Link>
                  );
                })}
              </div>
              <UserButton
                userProfileMode="navigation"
                userProfileUrl="/account"
                appearance={{
                  elements: {
                    avatarBox: "w-8 h-8",
                  },
                }}
              />
            </>
          ) : (
            <Link href="/sign-in">
              <Button className="hover:scale-105">
                Sign In
              </Button>
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
