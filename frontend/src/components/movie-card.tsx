import Image from "next/image";
import { Star, ThumbsDown, ThumbsUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { MovieRecommendation } from "@/lib/types";

type MovieCardProps = {
  movie: MovieRecommendation;
  priority?: boolean;
  onFeedback?: (movie: MovieRecommendation, sentiment: "up" | "down") => void;
  onSaveToWatchlist?: (movie: MovieRecommendation) => void;
  onMarkWatched?: (movie: MovieRecommendation) => void;
  actionsDisabled?: boolean;
  watchlistState?: "idle" | "saving" | "saved" | "error";
  watchedState?: "idle" | "saving" | "saved" | "error";
};

export function MovieCard({
  movie,
  priority = false,
  onFeedback,
  onSaveToWatchlist,
  onMarkWatched,
  actionsDisabled = false,
  watchlistState = "idle",
  watchedState = "idle"
}: MovieCardProps) {
  const imageUrl = movie.poster_url || movie.backdrop_url;

  return (
    <Card className="group relative h-full min-h-[31rem] overflow-hidden border-white/10 bg-black/30 transition duration-300 hover:-translate-y-1.5 hover:border-primary/50">
      <div className="absolute inset-0">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={`${movie.title} poster`}
            fill
            sizes="(max-width: 768px) 300px, 340px"
            className="object-cover transition duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="h-full w-full bg-gradient-to-br from-slate-900 via-slate-800 to-rose-950" />
        )}
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-black via-black/55 to-black/10" />
      <div className="absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-black/60 to-transparent" />
      <CardContent className="relative flex h-full flex-col justify-end gap-4 p-5">
        <div className="flex items-center justify-between">
          <Badge className="max-w-[70%] truncate border-white/15 bg-white/10 text-white/85">
            {movie.genre}
          </Badge>
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-black/30 px-3 py-1 text-sm text-amber-300">
            <Star className="size-3.5 fill-current" />
            <span>{movie.rating.toFixed(1)}</span>
          </div>
        </div>

        <div>
          <h3 className="text-2xl font-semibold text-white">{movie.title}</h3>
          <p className="mt-2 text-sm text-slate-300">
            {movie.year > 0 ? movie.year : "Unknown year"}
            {movie.runtime ? ` • ${movie.runtime}` : ""}
            {priority ? " • Signature pick" : ""}
          </p>
        </div>

        <p className="text-sm leading-6 text-slate-200/85">
          {movie.reason}
        </p>

        <div className="rounded-2xl border border-white/10 bg-black/25 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Why it fits</p>
          <p className="mt-2 text-sm leading-6 text-slate-200">{movie.tagline || "TMDB result matched your prompt."}</p>
        </div>

        {onFeedback || onSaveToWatchlist || onMarkWatched ? (
          <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/30 px-3 py-2">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
              Account actions
            </p>
            <div className="flex flex-wrap justify-end gap-2">
              {onSaveToWatchlist ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="rounded-full text-sky-200 hover:bg-sky-500/10 hover:text-sky-100"
                  onClick={() => onSaveToWatchlist(movie)}
                  disabled={actionsDisabled || watchlistState === "saving"}
                >
                  {watchlistState === "saving"
                    ? "Saving..."
                    : watchlistState === "saved"
                    ? "Saved"
                    : watchlistState === "error"
                    ? "Retry save"
                    : "Save"}
                </Button>
              ) : null}
              {onMarkWatched ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="rounded-full text-amber-100 hover:bg-amber-500/10"
                  onClick={() => onMarkWatched(movie)}
                  disabled={actionsDisabled || watchedState === "saving"}
                >
                  {watchedState === "saving"
                    ? "Saving..."
                    : watchedState === "saved"
                    ? "Watched"
                    : watchedState === "error"
                    ? "Retry watched"
                    : "Watched"}
                </Button>
              ) : null}
              {onFeedback ? (
                <>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="rounded-full text-emerald-200 hover:bg-emerald-500/10 hover:text-emerald-100"
                    onClick={() => onFeedback(movie, "up")}
                    disabled={actionsDisabled}
                  >
                    <ThumbsUp className="size-4" />
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="rounded-full text-rose-200 hover:bg-rose-500/10 hover:text-rose-100"
                    onClick={() => onFeedback(movie, "down")}
                    disabled={actionsDisabled}
                  >
                    <ThumbsDown className="size-4" />
                  </Button>
                </>
              ) : null}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
