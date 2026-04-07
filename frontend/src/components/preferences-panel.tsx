"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Heart, SlidersHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { UserPreference, UserPreferenceUpdate } from "@/lib/types";

const genreOptions = [
  "Action",
  "Animation",
  "Comedy",
  "Drama",
  "Family",
  "Horror",
  "Mystery",
  "Romance",
  "Sci-Fi",
  "Thriller"
];

const vibeOptions = ["Warm", "Emotional", "Thoughtful", "Light", "Dark", "Cozy"];
const decadeOptions = ["1980s", "1990s", "2000s", "2010s", "2020s"];
const complexityOptions = [
  { label: "Light", value: "light" },
  { label: "Balanced", value: "balanced" },
  { label: "Challenging", value: "challenging" }
];

type PreferencesPanelProps = {
  preferences: UserPreference | null;
  onSave: (payload: UserPreferenceUpdate) => Promise<void>;
  isSaving?: boolean;
};

export function PreferencesPanel({
  preferences,
  onSave,
  isSaving = false
}: PreferencesPanelProps) {
  const [favoriteMoviesText, setFavoriteMoviesText] = useState("");
  const [dislikedMoviesText, setDislikedMoviesText] = useState("");

  const draft = useMemo<UserPreferenceUpdate>(
    () => ({
      favorite_genres: preferences?.favorite_genres ?? [],
      disliked_genres: preferences?.disliked_genres ?? [],
      favorite_movies: preferences?.favorite_movies ?? [],
      disliked_movies: preferences?.disliked_movies ?? [],
      preferred_decades: preferences?.preferred_decades ?? [],
      vibe_preferences: preferences?.vibe_preferences ?? [],
      avoid_gore: preferences?.avoid_gore ?? false,
      avoid_sad_endings: preferences?.avoid_sad_endings ?? false,
      complexity_preference: preferences?.complexity_preference ?? "balanced"
    }),
    [preferences]
  );

  const toggleItem = (items: string[], value: string) =>
    items.includes(value)
      ? items.filter((item) => item !== value)
      : [...items, value];

  const handleSave = async () => {
    const favoriteMovies = parseList(favoriteMoviesText, draft.favorite_movies);
    const dislikedMovies = parseList(dislikedMoviesText, draft.disliked_movies);

    await onSave({
      ...draft,
      favorite_movies: favoriteMovies,
      disliked_movies: dislikedMovies
    });
    setFavoriteMoviesText("");
    setDislikedMoviesText("");
  };

  const updateDraft = async (next: UserPreferenceUpdate) => {
    await onSave(next);
  };

  return (
    <section className="rounded-[2rem] border border-white/10 bg-black/25 p-6 backdrop-blur-xl">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex size-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
          <SlidersHorizontal className="size-5 text-primary" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">
            Taste Profile
          </p>
          <h3 className="mt-1 text-xl font-semibold text-white">
            Shape future recommendations
          </h3>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <PreferenceGroup title="Favorite genres">
          {genreOptions.map((genre) => (
            <ChipButton
              key={`favorite-${genre}`}
              active={draft.favorite_genres.includes(genre)}
              onClick={() =>
                updateDraft({
                  ...draft,
                  favorite_genres: toggleItem(draft.favorite_genres, genre),
                  disliked_genres: draft.disliked_genres.filter((item) => item !== genre)
                })
              }
            >
              {genre}
            </ChipButton>
          ))}
        </PreferenceGroup>

        <PreferenceGroup title="Avoid genres">
          {genreOptions.map((genre) => (
            <ChipButton
              key={`avoid-${genre}`}
              active={draft.disliked_genres.includes(genre)}
              tone="muted"
              onClick={() =>
                updateDraft({
                  ...draft,
                  disliked_genres: toggleItem(draft.disliked_genres, genre),
                  favorite_genres: draft.favorite_genres.filter((item) => item !== genre)
                })
              }
            >
              {genre}
            </ChipButton>
          ))}
        </PreferenceGroup>

        <PreferenceGroup title="Preferred decades">
          {decadeOptions.map((decade) => (
            <ChipButton
              key={decade}
              active={draft.preferred_decades.includes(decade)}
              onClick={() =>
                updateDraft({
                  ...draft,
                  preferred_decades: toggleItem(draft.preferred_decades, decade)
                })
              }
            >
              {decade}
            </ChipButton>
          ))}
        </PreferenceGroup>

        <PreferenceGroup title="Vibe preferences">
          {vibeOptions.map((vibe) => (
            <ChipButton
              key={vibe}
              active={draft.vibe_preferences.includes(vibe)}
              onClick={() =>
                updateDraft({
                  ...draft,
                  vibe_preferences: toggleItem(draft.vibe_preferences, vibe)
                })
              }
            >
              {vibe}
            </ChipButton>
          ))}
        </PreferenceGroup>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1fr_0.8fr]">
        <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
          <p className="text-sm font-medium text-white">Favorite movies</p>
          <textarea
            value={favoriteMoviesText}
            onChange={(event) => setFavoriteMoviesText(event.target.value)}
            placeholder="Interstellar, Arrival, Her"
            className="mt-3 min-h-24 w-full rounded-2xl border border-white/10 bg-black/30 p-3 text-sm text-white outline-none"
          />
          <TagList items={draft.favorite_movies} />
        </div>

        <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
          <p className="text-sm font-medium text-white">Movies to avoid</p>
          <textarea
            value={dislikedMoviesText}
            onChange={(event) => setDislikedMoviesText(event.target.value)}
            placeholder="Saw, Transformers..."
            className="mt-3 min-h-24 w-full rounded-2xl border border-white/10 bg-black/30 p-3 text-sm text-white outline-none"
          />
          <TagList items={draft.disliked_movies} />
        </div>

        <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
          <p className="text-sm font-medium text-white">Guardrails</p>
          <div className="mt-4 flex flex-col gap-3">
            {complexityOptions.map((option) => (
              <Button
                key={option.value}
                variant={draft.complexity_preference === option.value ? "default" : "outline"}
                className="justify-start rounded-2xl"
                onClick={() =>
                  updateDraft({
                    ...draft,
                    complexity_preference: option.value
                  })
                }
              >
                {option.label}
              </Button>
            ))}
            <Button
              variant={draft.avoid_gore ? "default" : "outline"}
              className="justify-start rounded-2xl"
              onClick={() =>
                updateDraft({
                  ...draft,
                  avoid_gore: !draft.avoid_gore
                })
              }
            >
              Avoid gore
            </Button>
            <Button
              variant={draft.avoid_sad_endings ? "default" : "outline"}
              className="justify-start rounded-2xl"
              onClick={() =>
                updateDraft({
                  ...draft,
                  avoid_sad_endings: !draft.avoid_sad_endings
                })
              }
            >
              Avoid sad endings
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between gap-4">
        <p className="text-sm text-slate-400">
          Thumbs up and thumbs down on recommendations will keep refining this profile.
        </p>
        <Button onClick={handleSave} disabled={isSaving} className="rounded-full px-6">
          <Heart className="size-4" />
          {isSaving ? "Saving..." : "Save movie picks"}
        </Button>
      </div>
    </section>
  );
}

function PreferenceGroup({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
      <p className="mb-3 text-sm font-medium text-white">{title}</p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

function ChipButton({
  active,
  children,
  onClick,
  tone = "primary"
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
  tone?: "primary" | "muted";
}) {
  const activeClass =
    tone === "primary"
      ? "border-primary/60 bg-primary/15 text-white"
      : "border-rose-400/50 bg-rose-500/10 text-rose-100";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm transition ${
        active
          ? activeClass
          : "border-white/10 bg-black/20 text-slate-300 hover:border-white/20 hover:text-white"
      }`}
    >
      {children}
    </button>
  );
}

function TagList({ items }: { items: string[] }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {items.map((item) => (
        <Badge
          key={item}
          className="border-white/10 bg-black/30 text-slate-200"
        >
          {item}
        </Badge>
      ))}
    </div>
  );
}

function parseList(value: string, fallback: string[]) {
  const parsed = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return parsed.length ? parsed : fallback;
}
