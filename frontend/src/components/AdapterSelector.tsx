"use client";

import { useEffect, useState } from "react";
import { api, LoRAAdapter } from "@/lib/api";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Wand2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  value: string | null;
  onChange: (adapterId: string | null) => void;
}

export default function AdapterSelector({ value, onChange }: Props) {
  const [adapters, setAdapters] = useState<LoRAAdapter[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listAdapters()
      .then((res) => setAdapters(res.items))
      .catch(() => setAdapters([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading || adapters.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1">
        <Label className="text-sm font-medium text-muted-foreground">
          Custom Style
        </Label>
        <Badge variant="secondary" className="text-[10px]">
          optional
        </Badge>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onChange(null)}
          className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border transition-all duration-200 cursor-pointer",
            value === null
              ? "bg-[#1DB954] border-[#1DB954] text-black font-bold"
              : "border-[#727272] text-[#B3B3B3] hover:border-white hover:text-white hover:bg-[#282828]"
          )}
        >
          Default
        </button>
        {adapters.map((adapter) => (
          <button
            key={adapter.id}
            type="button"
            onClick={() => onChange(adapter.id)}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border transition-all duration-200 cursor-pointer",
              value === adapter.id
                ? "bg-[#1DB954] border-[#1DB954] text-black font-bold"
                : "border-[#727272] text-[#B3B3B3] hover:border-white hover:text-white hover:bg-[#282828]"
            )}
          >
            <Wand2 className="w-3 h-3" />
            {adapter.name}
          </button>
        ))}
      </div>
    </div>
  );
}
