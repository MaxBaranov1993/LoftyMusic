"use client";

import { cn } from "@/lib/utils";

export function Equalizer({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-end gap-[2px] h-4", className)}>
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="w-[3px] bg-primary rounded-full animate-equalizer"
          style={{
            animationDelay: `${i * 0.15}s`,
            animationDuration: `${0.8 + i * 0.15}s`,
          }}
        />
      ))}
    </div>
  );
}
