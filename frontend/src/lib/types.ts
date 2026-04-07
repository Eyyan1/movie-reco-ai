export type MovieRecommendation = {
  id: number;
  title: string;
  year: number;
  genre: string;
  runtime: string | null;
  rating: number;
  tagline: string;
  reason: string;
  poster_url: string;
  backdrop_url: string;
};

export type RecommendationGroup = {
  group_title: string;
  description: string;
  movies: MovieRecommendation[];
};

export type RecommendationResponse = {
  summary: string;
  groups: RecommendationGroup[];
};

export type UserPreference = {
  user_id: string;
  favorite_genres: string[];
  disliked_genres: string[];
  favorite_movies: string[];
  disliked_movies: string[];
  preferred_decades: string[];
  vibe_preferences: string[];
  avoid_gore: boolean;
  avoid_sad_endings: boolean;
  complexity_preference: string | null;
};

export type UserPreferenceUpdate = Omit<UserPreference, "user_id">;

export type RecommendationFeedbackPayload = {
  movie_id: number;
  movie_title: string;
  movie_genre: string;
  sentiment: "up" | "down";
};

export type AuthUser = {
  id: string;
  email: string;
};

export type AuthResponse = {
  user: AuthUser;
};

export type AuthPayload = {
  email: string;
  password: string;
};

export type WatchlistResponse = {
  items: MovieRecommendation[];
};

export type WatchedHistoryResponse = {
  items: MovieRecommendation[];
};
