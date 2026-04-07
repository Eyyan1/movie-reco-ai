"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bot, Film, Sparkles, Stars } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { AccountMenu } from "@/components/account-menu";
import { ChatInput } from "@/components/chat-input";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { MovieCarousel } from "@/components/movie-carousel";
import { PreferencesPanel } from "@/components/preferences-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  addToWatchlist,
  fetchPreferences,
  fetchRecommendations,
  markWatched,
  savePreferences,
  submitRecommendationFeedback
} from "@/lib/api";
import type {
  MovieRecommendation,
  RecommendationResponse,
  UserPreference,
  UserPreferenceUpdate
} from "@/lib/types";

const examplePrompts = [
  "Give me smart sci-fi with emotional weight",
  "I want stylish thrillers like Gone Girl",
  "Recommend feel-good movies for a cozy night",
  "Find dark, mind-bending films with great endings"
];

export function HomePage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [preferences, setPreferences] = useState<UserPreference | null>(null);
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [watchlistStateByMovieId, setWatchlistStateByMovieId] = useState<
    Record<number, "idle" | "saving" | "saved" | "error">
  >({});
  const [watchedStateByMovieId, setWatchedStateByMovieId] = useState<
    Record<number, "idle" | "saving" | "saved" | "error">
  >({});

  useEffect(() => {
    if (!user) {
      setPreferences(null);
      return;
    }

    fetchPreferences(user.id)
      .then(setPreferences)
      .catch(() => {
        setPreferences(null);
      });
  }, [user]);

  const handlePrompt = async (prompt: string) => {
    setError(null);
    setNotice(null);
    setIsLoading(true);

    try {
      const response = await fetchRecommendations(prompt);
      setResult(response);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Something went wrong while fetching recommendations.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSavePreferences = async (payload: UserPreferenceUpdate) => {
    if (!user) {
      setError("Create an account to save preferences.");
      return;
    }

    setError(null);
    setNotice(null);
    setIsSavingPreferences(true);
    try {
      const saved = await savePreferences(user.id, payload);
      setPreferences(saved);
      setNotice("Taste profile updated.");
    } catch {
      setError("Unable to save your taste profile right now.");
    } finally {
      setIsSavingPreferences(false);
    }
  };

  const handleFeedback = async (
    movie: MovieRecommendation,
    sentiment: "up" | "down"
  ) => {
    if (!user) {
      setError("Sign in to save recommendation feedback.");
      return;
    }

    setError(null);
    setNotice(null);
    try {
      const updated = await submitRecommendationFeedback(user.id, {
        movie_id: movie.id,
        movie_title: movie.title,
        movie_genre: movie.genre,
        sentiment
      });
      setPreferences(updated);
      setNotice(`Saved your feedback for ${movie.title}.`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to save your recommendation feedback right now."
      );
    }
  };

  const handleSaveToWatchlist = async (movie: MovieRecommendation) => {
    if (!user) {
      setError("Sign in to save movies to your watchlist.");
      return;
    }
    setError(null);
    setNotice(null);
    setWatchlistStateByMovieId((current) => ({ ...current, [movie.id]: "saving" }));
    try {
      await addToWatchlist(movie);
      setWatchlistStateByMovieId((current) => ({ ...current, [movie.id]: "saved" }));
      setNotice(`${movie.title} was added to your watchlist.`);
    } catch (requestError) {
      setWatchlistStateByMovieId((current) => ({ ...current, [movie.id]: "error" }));
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to add this movie to your watchlist right now."
      );
    }
  };

  const handleMarkWatched = async (movie: MovieRecommendation) => {
    if (!user) {
      setError("Sign in to track watched movies.");
      return;
    }
    setError(null);
    setNotice(null);
    setWatchedStateByMovieId((current) => ({ ...current, [movie.id]: "saving" }));
    try {
      await markWatched(movie);
      setWatchedStateByMovieId((current) => ({ ...current, [movie.id]: "saved" }));
      setNotice(`${movie.title} was marked as watched.`);
    } catch (requestError) {
      setWatchedStateByMovieId((current) => ({ ...current, [movie.id]: "error" }));
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to mark this movie as watched right now."
      );
    }
  };

  return (
    <main className="relative overflow-hidden">
      <div className="absolute inset-0 cinematic-grid opacity-60" />
      <div className="absolute left-0 top-0 h-96 w-96 rounded-full bg-primary/25 blur-3xl" />
      <div className="absolute right-0 top-24 h-[28rem] w-[28rem] rounded-full bg-blue-500/15 blur-3xl" />

      <section className="relative min-h-screen px-6 pb-20 pt-10 md:px-10 lg:px-16">
        <div className="mx-auto flex min-h-[calc(100svh-2.5rem)] max-w-7xl flex-col justify-between">
          <header className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 backdrop-blur">
                <Film className="text-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-muted-foreground">
                  Movie Reco AI
                </p>
                <p className="text-sm text-white/80">
                  Precision picks for every mood.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge className="border-white/10 bg-white/5 text-white/80">
                Powered by TMDB
              </Badge>
              <AccountMenu />
            </div>
          </header>

          <div className="grid gap-14 pb-10 pt-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
            <motion.div
              initial={{ opacity: 0, y: 22 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: "easeOut" }}
              className="max-w-3xl"
            >
              <div className="mb-6 flex items-center gap-3 text-sm text-white/70">
                <Stars className="size-4 text-primary" />
                <span>Ask for moods, genres, pacing, endings, or hidden gems.</span>
              </div>
              <h1 className="max-w-4xl text-5xl font-semibold leading-none tracking-tight md:text-7xl">
                Find your next
                <span className="text-gradient"> unforgettable movie night</span>
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
                Describe exactly what you want to feel and get curated recommendation
                groups with rich picks instead of a flat list.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 26 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.12, ease: "easeOut" }}
              className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur-xl"
            >
              <div className="mb-4 flex items-center gap-3 text-sm text-white/80">
                <Bot className="size-4 text-primary" />
                <span>Prompt the recommendation engine</span>
              </div>
              <ChatInput onSubmit={handlePrompt} isLoading={isLoading} />
              <div className="mt-5 flex flex-wrap gap-2">
                {examplePrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handlePrompt(prompt)}
                    className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/75 transition hover:border-primary/60 hover:bg-primary/10 hover:text-white"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.18, ease: "easeOut" }}
            className="grid gap-4 md:grid-cols-3"
          >
            {[
              {
                title: "Mood-aware prompts",
                body: "Describe atmosphere, tone, pace, and emotion in natural language."
              },
              {
                title: "Grouped recommendations",
                body: "Receive curated collections built around why each movie fits."
              },
              {
                title: "Instant API flow",
                body: "Next.js talks directly to FastAPI, which now fetches real TMDB movie data."
              }
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-[1.5rem] border border-white/10 bg-black/30 p-5 backdrop-blur"
              >
                <div className="mb-3 flex items-center gap-2 text-sm text-primary">
                  <Sparkles className="size-4" />
                  <span>{item.title}</span>
                </div>
                <p className="text-sm leading-6 text-slate-300">{item.body}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      <section className="relative z-10 px-6 pb-10 md:px-10 lg:px-16">
        <div className="mx-auto max-w-7xl">
          {user ? (
            <PreferencesPanel
              preferences={preferences}
              onSave={handleSavePreferences}
              isSaving={isSavingPreferences}
            />
          ) : (
            <div className="rounded-[2rem] border border-white/10 bg-black/25 p-6 backdrop-blur-xl">
              <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">
                Account Benefits
              </p>
              <h3 className="mt-3 text-2xl font-semibold text-white">
                Save taste preferences, watchlist picks, and watched history
              </h3>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
                Guest mode still works for recommendations. Sign in to make ranking adapt
                to your account and persist everything across sessions.
              </p>
              {!isAuthLoading ? (
                <div className="mt-5 flex gap-3">
                  <Button asChild variant="outline" className="rounded-full border-white/10 bg-white/5 text-white">
                    <Link href="/login">
                      Sign in
                    </Link>
                  </Button>
                  <Button asChild className="rounded-full">
                    <Link href="/signup">Create account</Link>
                  </Button>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </section>

      <section className="relative z-10 px-6 pb-24 md:px-10 lg:px-16">
        <div className="mx-auto max-w-7xl rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-black/30 backdrop-blur-xl md:p-8">
          <div className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-muted-foreground">
                Recommendation Feed
              </p>
              <h2 className="mt-3 text-3xl font-semibold text-white">
                Rich results built for browsing
              </h2>
            </div>
            {result ? (
              <p className="max-w-2xl text-sm leading-6 text-slate-300">{result.summary}</p>
            ) : (
              <p className="max-w-xl text-sm leading-6 text-slate-400">
                Start with one of the prompt chips above, or write your own request to
                see grouped recommendations.
              </p>
            )}
          </div>

          {notice ? (
            <div className="mb-6 rounded-[1.5rem] border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              {notice}
            </div>
          ) : null}

          {isLoading ? (
            <LoadingSkeleton />
          ) : error ? (
            <div className="rounded-[1.5rem] border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-100">
              {error}
            </div>
          ) : result ? (
            <div className="flex flex-col gap-10">
              {result.groups.map((group, index) => (
                <MovieCarousel
                  key={group.group_title}
                  group={group}
                  priority={index === 0}
                  onFeedback={handleFeedback}
                  onSaveToWatchlist={handleSaveToWatchlist}
                  onMarkWatched={handleMarkWatched}
                  actionsDisabled={false}
                  watchlistStateByMovieId={watchlistStateByMovieId}
                  watchedStateByMovieId={watchedStateByMovieId}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-[1.75rem] border border-dashed border-white/10 bg-black/20 px-6 py-16 text-center">
              <p className="text-lg text-white">No recommendations yet</p>
              <p className="mt-3 text-sm text-slate-400">
                Ask for a vibe like "tense psychological thrillers with elegant visuals".
              </p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
