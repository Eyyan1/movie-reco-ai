"use client";

import { useState } from "react";
import { LoaderCircle, SendHorizonal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type ChatInputProps = {
  onSubmit: (prompt: string) => void;
  isLoading?: boolean;
};

export function ChatInput({ onSubmit, isLoading = false }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const prompt = value.trim();
    if (!prompt || isLoading) {
      return;
    }

    onSubmit(prompt);
  };

  return (
    <div className="flex flex-col gap-4">
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Tell me what kind of movie night you want..."
        className="min-h-32 rounded-[1.5rem] border-white/10 bg-black/30 px-5 py-4 text-base text-white placeholder:text-slate-500 focus-visible:ring-primary/40"
      />
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-slate-400">
          Try genres, moods, pace, actors, or “more like...”
        </p>
        <Button
          onClick={handleSubmit}
          disabled={isLoading}
          className="min-w-36 rounded-full px-6"
        >
          {isLoading ? (
            <LoaderCircle className="animate-spin" data-icon="inline-start" />
          ) : (
            <SendHorizonal data-icon="inline-start" />
          )}
          {isLoading ? "Thinking..." : "Get Picks"}
        </Button>
      </div>
    </div>
  );
}

