"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchWatchedHistory, fetchWatchlist, markWatched, removeFromWatchlist } from "@/lib/api";
import type { MovieRecommendation } from "@/lib/types";
import { MovieCard } from "@/components/movie-card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";

export function WatchlistPage() {
  const { user, isLoading } = useAuth();
  const [watchlist, setWatchlist] = useState<MovieRecommendation[]>([]);
  const [history, setHistory] = useState<MovieRecommendation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      return;
    }

    Promise.all([fetchWatchlist(), fetchWatchedHistory()])
      .then(([watchlistResponse, historyResponse]) => {
        setWatchlist(watchlistResponse.items);
        setHistory(historyResponse.items);
      })
      .catch(() => {
        setError("Unable to load your saved library right now.");
      });
  }, [user]);

  const handleRemove = async (movie: MovieRecommendation) => {
    const response = await removeFromWatchlist(movie.id);
    setWatchlist(response.items);
  };

  const handleWatched = async (movie: MovieRecommendation) => {
    const response = await markWatched(movie);
    setHistory(response.items);
    const watchlistResponse = await fetchWatchlist();
    setWatchlist(watchlistResponse.items);
  };

  if (isLoading) {
    return <div className="px-6 py-16 text-slate-300">Loading account...</div>;
  }

  if (!user) {
    return (
      <div className="min-h-screen px-6 py-16 md:px-10 lg:px-16">
        <div className="mx-auto max-w-3xl rounded-[2rem] border border-white/10 bg-black/25 p-8 text-center">
          <h1 className="text-3xl font-semibold text-white">Sign in to see your library</h1>
          <p className="mt-4 text-slate-300">
            Watchlist and watched history are tied to your account.
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Button asChild variant="outline" className="rounded-full border-white/10 bg-white/5 text-white">
              <Link href="/login">
                Sign in
              </Link>
            </Button>
            <Button asChild className="rounded-full">
              <Link href="/signup">Create account</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen px-6 py-12 md:px-10 lg:px-16">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-muted-foreground">
              Your Library
            </p>
            <h1 className="mt-3 text-5xl font-semibold text-white">Watchlist and history</h1>
          </div>
          <Button asChild variant="outline" className="rounded-full border-white/10 bg-white/5 text-white">
            <Link href="/">
              Back home
            </Link>
          </Button>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            {error}
          </div>
        ) : null}

        <section className="mb-12">
          <h2 className="mb-5 text-2xl font-semibold text-white">Watchlist</h2>
          {watchlist.length ? (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {watchlist.map((movie) => (
                <div key={`watchlist-${movie.id}`} className="space-y-3">
                  <MovieCard movie={movie} />
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1 rounded-full border-white/10 bg-white/5 text-white"
                      onClick={() => handleWatched(movie)}
                    >
                      Mark watched
                    </Button>
                    <Button
                      variant="ghost"
                      className="rounded-full text-rose-200 hover:bg-rose-500/10"
                      onClick={() => handleRemove(movie)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState text="No watchlist items yet. Save movies from the recommendation feed." />
          )}
        </section>

        <section>
          <h2 className="mb-5 text-2xl font-semibold text-white">Watched history</h2>
          {history.length ? (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {history.map((movie) => (
                <MovieCard key={`history-${movie.id}`} movie={movie} />
              ))}
            </div>
          ) : (
            <EmptyState text="Nothing marked as watched yet." />
          )}
        </section>
      </div>
    </main>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-[1.75rem] border border-dashed border-white/10 bg-black/20 px-6 py-12 text-center text-slate-400">
      {text}
    </div>
  );
}
