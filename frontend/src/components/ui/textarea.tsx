import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex field-sizing-content min-h-16 w-full rounded-lg border border-[#282828] bg-[#282828] px-3 py-2 text-base text-white transition-[color,box-shadow] outline-none placeholder:text-[#727272] focus-visible:border-[#1DB954] focus-visible:ring-[3px] focus-visible:ring-[#1DB954]/20 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 md:text-sm",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
