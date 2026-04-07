"use client";

import { useRef } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MovieCard } from "@/components/movie-card";
import { Button } from "@/components/ui/button";
import type { MovieRecommendation, RecommendationGroup } from "@/lib/types";

type MovieCarouselProps = {
  group: RecommendationGroup;
  priority?: boolean;
  onFeedback?: (movie: MovieRecommendation, sentiment: "up" | "down") => void;
  onSaveToWatchlist?: (movie: MovieRecommendation) => void;
  onMarkWatched?: (movie: MovieRecommendation) => void;
  actionsDisabled?: boolean;
  watchlistStateByMovieId?: Record<number, "idle" | "saving" | "saved" | "error">;
  watchedStateByMovieId?: Record<number, "idle" | "saving" | "saved" | "error">;
};

export function MovieCarousel({
  group,
  priority = false,
  onFeedback,
  onSaveToWatchlist,
  onMarkWatched,
  actionsDisabled = false,
  watchlistStateByMovieId = {},
  watchedStateByMovieId = {}
}: MovieCarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollByAmount = (direction: "left" | "right") => {
    scrollRef.current?.scrollBy({
      left: direction === "right" ? 360 : -360,
      behavior: "smooth"
    });
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.55, ease: "easeOut" }}
      className="flex flex-col gap-5"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-primary/80">Collection</p>
          <h3 className="mt-2 text-2xl font-semibold text-white">{group.group_title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
            {group.description}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10"
            onClick={() => scrollByAmount("left")}
          >
            <ChevronLeft />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="rounded-full border-white/10 bg-white/5 text-white hover:bg-white/10"
            onClick={() => scrollByAmount("right")}
          >
            <ChevronRight />
          </Button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex snap-x snap-mandatory gap-5 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {group.movies.map((movie, index) => (
          <div
            key={`${group.group_title}-${movie.title}`}
            className="min-w-[300px] snap-start basis-[300px] md:min-w-[340px] md:basis-[340px]"
          >
            <MovieCard
              movie={movie}
              priority={priority && index === 0}
              onFeedback={onFeedback}
              onSaveToWatchlist={onSaveToWatchlist}
              onMarkWatched={onMarkWatched}
              actionsDisabled={actionsDisabled}
              watchlistState={watchlistStateByMovieId[movie.id] ?? "idle"}
              watchedState={watchedStateByMovieId[movie.id] ?? "idle"}
            />
          </div>
        ))}
      </div>
    </motion.section>
  );
}
