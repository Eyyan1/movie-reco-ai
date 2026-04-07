import type {
  AuthPayload,
  AuthResponse,
  AuthUser,
  RecommendationFeedbackPayload,
  RecommendationResponse,
  UserPreference,
  UserPreferenceUpdate,
  WatchedHistoryResponse,
  WatchlistResponse,
  MovieRecommendation
} from "@/lib/types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
  } catch {}
  return fallback;
}

export async function fetchRecommendations(
  prompt: string,
  userId?: string
): Promise<RecommendationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/recommendations`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ prompt, user_id: userId })
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Unable to fetch recommendations from the backend.")
    );
  }

  return response.json();
}

export async function fetchPreferences(userId: string): Promise<UserPreference> {
  const response = await fetch(`${API_BASE_URL}/api/v1/preferences/me`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to load saved preferences."));
  }

  return response.json();
}

export async function savePreferences(
  _userId: string,
  payload: UserPreferenceUpdate
): Promise<UserPreference> {
  const response = await fetch(`${API_BASE_URL}/api/v1/preferences/me`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to save preferences."));
  }

  return response.json();
}

export async function submitRecommendationFeedback(
  _userId: string,
  payload: RecommendationFeedbackPayload
): Promise<UserPreference> {
  const response = await fetch(`${API_BASE_URL}/api/v1/preferences/feedback`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Unable to save recommendation feedback.")
    );
  }

  return response.json();
}

export async function signUp(payload: AuthPayload): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/signup`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to create account."));
  }
  return response.json();
}

export async function login(payload: AuthPayload): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to sign in."));
  }
  return response.json();
}

export async function logout(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to sign out."));
  }
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: "GET",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to load current account."));
  }
  return response.json();
}

export async function fetchWatchlist(): Promise<WatchlistResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/watchlist`, {
    method: "GET",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to load watchlist."));
  }
  return response.json();
}

export async function addToWatchlist(movie: MovieRecommendation): Promise<WatchlistResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/watchlist`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(movie)
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to save to watchlist."));
  }
  return response.json();
}

export async function removeFromWatchlist(movieId: number): Promise<WatchlistResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/watchlist/${movieId}`, {
    method: "DELETE",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to remove from watchlist."));
  }
  return response.json();
}

export async function fetchWatchedHistory(): Promise<WatchedHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/history`, {
    method: "GET",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to load watched history."));
  }
  return response.json();
}

export async function markWatched(movie: MovieRecommendation): Promise<WatchedHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/history`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(movie)
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to mark movie as watched."));
  }
  return response.json();
}
