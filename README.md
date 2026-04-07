# Movie Reco AI

Full-stack movie recommendation app with a cinematic Next.js frontend and a FastAPI backend.

The app now uses live TMDB movie data for recommendations.
It can optionally use OpenAI to parse free-text movie intent before TMDB retrieval.
It can also optionally use OpenAI embeddings to rerank the `Best Match` rail for higher semantic quality.
It now supports account-based personalization, watchlists, and watched history with PostgreSQL persistence.

## Stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, Framer Motion, shadcn/ui-style components
- Backend: FastAPI, Python, PostgreSQL, SQLAlchemy

## Project Structure

```text
frontend/
backend/
```

## Setup

### 1. Frontend

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`.

### 2. Backend

```bash
cd backend
python -m pip install --user -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Backend runs on `http://localhost:8000`.

## Environment Variables

### Frontend

`frontend/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Backend

`backend/.env`

```env
APP_NAME=Movie Reco AI API
APP_ENV=development
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/movie_reco_ai
FRONTEND_ORIGIN=http://localhost:3000
TMDB_API_KEY=your_tmdb_bearer_token
TMDB_BASE_URL=https://api.themoviedb.org/3
TMDB_IMAGE_BASE_URL=https://image.tmdb.org/t/p/w500
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=512
AUTH_COOKIE_NAME=movie_reco_session
AUTH_SESSION_HOURS=168
```

## API

- `GET /api/v1/health`
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/recommendations`
- `GET /api/v1/preferences/me`
- `PUT /api/v1/preferences/me`
- `POST /api/v1/preferences/feedback`
- `GET /api/v1/watchlist`
- `POST /api/v1/watchlist`
- `DELETE /api/v1/watchlist/{movie_id}`
- `GET /api/v1/history`
- `POST /api/v1/history`

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/recommendations ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"I want emotional sci-fi movies with strong visuals\"}"
```

Example health check:

```bash
curl http://localhost:8000/api/v1/health
```

## TMDB Notes

- Create a TMDB account and generate an API Read Access Token (Bearer token).
- Put that token into `backend/.env` as `TMDB_API_KEY`.
- Image URLs are built from `TMDB_IMAGE_BASE_URL` and TMDB `poster_path` or `backdrop_path`.
- This product uses the TMDB API but is not endorsed or certified by TMDB.

## AI Parsing

- If `OPENAI_API_KEY` is set, the backend performs one OpenAI intent-parse call per request, then uses TMDB for final retrieval and ranking.
- If `OPENAI_API_KEY` is missing, the model returns malformed output, or structured parsing fails validation, the backend retries once and then falls back to the existing rule-based parser.
- OpenAI parsing improves prompts such as:
  - `something like Interstellar but less confusing`
  - `a fun movie for date night`
  - `not too scary horror`
  - `movie starring tom holland`

### Expanded Intent Schema

The parser now decomposes prompts into a richer internal schema with fields such as:

- `query_type`
- `reference_titles`
- `genres`
- `subgenres`
- `tone`
- `moods`
- `emotional_targets`
- `themes`
- `narrative_targets`
- `story_outcomes`
- `ending_type`
- `character_dynamics`
- `setting`
- `scale`
- `pacing`
- `complexity`
- `violence_level`
- `audience`
- `year`
- `release_preference`
- `person`
- `language`
- `animation`
- `anime`
- `must_have`
- `nice_to_have`
- `exclude_terms`
- `avoid_genres`
- `avoid_elements`

The service also builds an internal retrieval-oriented rewrite string from that schema. It is used only for retrieval and reranking, not returned by the API.

### Narrative And Emotion Scoring

The `Best Match` rail now adds a dedicated narrative and emotion layer on top of TMDB retrieval, family-aware filtering, and embedding reranking.

- Emotional scoring boosts grief, loss, heartbreak, love, healing, warmth, friendship, hope, reunion, and bittersweet relationship cues when they match the parsed request.
- Narrative scoring boosts explicit story outcomes such as `villain wins`, `tragic ending`, `bittersweet ending`, `happy ending`, `revenge`, `sacrifice`, `redemption`, `twist ending`, and `underdog story`.
- Healing-style prompts now add extra weight for family conflict, reconciliation, forgiveness, second-chance arcs, cry-worthy romance, and relationship-centered drama instead of falling back to emotionally flat candidates.
- The pipeline also applies mismatch penalties, so prompts like `movie to cry to` push down action spectacle, family-comedy drift, superhero noise, and unrelated blockbuster results.
- Reference prompts with modifiers such as `like Arrival but warmer` or `like Interstellar but less confusing` use those modifiers during reranking instead of relying only on broad genre overlap.
- Zero-result prompts now go through staged recovery: parsed rewrite string, simplified soft-intent terms, family-aware genre discovery, and theme-aware discovery before the backend gives up.

This improves prompts like:

- `movie to cry to`
- `emotional family drama`
- `love story that will make me cry`
- `healing movie with heart`
- `villain wins`
- `like Arrival but warmer`
- `bittersweet romance`

### Intent Families

The parser also classifies each request into an `intent_family` so retrieval and ranking can use family-specific defaults instead of overfitting to individual prompts. Supported families are:

- `romance`
- `sad_emotional`
- `feel_good`
- `funny`
- `dark_intense`
- `reference`
- `narrative`
- `use_case`
- `constraint`
- `mixed`
- `general`

Examples:

- `love movie` -> `romance`
- `love but funny movie` -> `mixed`
- `sad movie` -> `sad_emotional`
- `movie to cry to` -> `sad_emotional`
- `emotional family drama` -> `sad_emotional`
- `healing movie with heart` -> `sad_emotional`
- `love story that will make me cry` -> `mixed`
- `feel good movie` -> `feel_good`
- `funny movie` -> `funny`
- `dark thriller` -> `dark_intense`
- `like Interstellar but less confusing` -> `reference`
- `movie where the villain wins` -> `narrative`
- `movie for date night` -> `use_case`
- `not too scary horror` -> `constraint`

### Family-Aware Defaults

The ranking pipeline now applies family-specific defaults, penalties, and fallback behavior:

- `romance` boosts romance/drama/comedy and relationship-centered themes while penalizing horror, crime, and broad action unless explicitly requested.
- `sad_emotional` boosts drama, romance, family drama, grief, heartbreak, loss, tragedy, and emotional healing while penalizing broad action, blockbusters, and horror drift.
- Healing and cry-worthy prompts stay in drama, romance, and family-drama fallback lanes, with extra scoring for reconciliation, recovery, sacrifice, terminal-illness, parent-child, and relationship-centered arcs.
- `feel_good` boosts comedy, romance, family, adventure, and light drama with warmth, healing, friendship, kindness, reunion, and comfort signals while penalizing horror, crime-heavy stories, bleak drama, warlike action, and dark psychological drift.
- `funny` boosts comedy, rom-com chemistry, witty banter, and lighter adventure while penalizing horror, bleak drama, crime-heavy tension, dark thrillers, warlike action, and emotionally punishing stories.
- `dark_intense` boosts thriller, mystery, drama, and darker psychological material while penalizing light family and broad comedy mismatch.
- `reference` stays anchored to the reference-title path and penalizes unrelated generic fallback behavior.
  Reference prompts now retry title resolution with normalized and simplified title variants, recover through similar/recommendations plus reference-genre discovery, and apply modifier-aware reranking for cues such as `darker`, `less dark`, `warmer`, `funnier`, `more emotional`, `less confusing`, `lighter`, and `more hopeful`.
  Non-animated reference prompts now hard-block animation and family drift unless the reference itself is animation/family or the user explicitly asks for it.
- `narrative` boosts story outcomes, endings, themes, and character dynamics such as villain-victory or tragic-ending requests.
- `use_case` applies defaults such as date-night, family-night, late-night-deep, or rainy-day fallback lanes even when no genre is explicit.
- `constraint` keeps exclusions such as `no gore`, `not too scary`, `no horror`, `no old movies`, or `not too long` active through fallback.
- `mixed` combines the strongest family signals instead of letting one erase the other.

This improves prompts like:

- `love movie` by treating it as a romance-family query instead of generic trending.
- `sad movie` by preferring emotional dramas instead of broad fallback.
- `love but funny movie` by combining romance and comedy defaults.
- `like Interstellar but less confusing` by keeping the request anchored to reference-family logic instead of drifting into generic fallback.
- `like Blade Runner 2049 but less dark` and `like Avengers: Infinity War but darker` by recovering the reference title more reliably and blocking animation/family drift unless it was explicitly requested.
- `uplifting movie`, `comfort movie`, and `easy movie for a relaxed night` by keeping fallback and reranking inside emotionally safe, warm, easy-to-enjoy territory.
- `laugh-out-loud movie`, `rom com with good banter`, and `fun movie` by keeping fallback and reranking inside comedy-first, light, chemistry-driven lanes instead of dark or crime-heavy drift.
- `emotional family drama`, `love story that will make me cry`, and `healing movie with heart` by keeping fallback and reranking inside emotional drama, family-drama, and cry-worthy romance lanes instead of thriller/action drift.
- `like Blade Runner 2049 but less dark` by recovering through normalized title resolution and reference-genre fallback instead of failing on a weak similar set.
- `like Avengers: Infinity War but darker` by keeping recovery inside blockbuster/reference lanes while blocking animation/family leakage.

### Supported Complex Prompt Shapes

Examples the parser is designed to represent well:

- `love movie`
- `sad movie`
- `heartbreaking romance`
- `like Arrival but warmer`
- `like Interstellar but less confusing`
- `movie starring Tom Holland`
- `stylish animated movie with emotional depth`
- `I want a movie like Avengers: Infinity War where the villain wins at the end`
- `not too scary horror`
- `fun movie for date night`

## Embedding Reranking

- If `OPENAI_API_KEY` is set, the backend can use OpenAI embeddings to rerank only the `Best Match` group.
- Embeddings are used selectively for:
  - title-similarity prompts such as `like Interstellar but less confusing`
  - richer descriptive prompts with multiple preferences
- TMDB remains the source of truth for candidate retrieval. Embeddings only reorder the existing `Best Match` candidate pool.
- Candidate embedding is bounded to a small batch and cached in memory by text hash.
- If `OPENAI_API_KEY` is missing, or the embedding request fails, the backend falls back to the existing heuristic TMDB ranking without failing the request.

## Evaluation Harness

The backend now includes a family-based evaluation harness under `backend/app/eval` so recommendation quality can be checked systematically across prompt families instead of debugging one prompt at a time.

Included benchmark families:

- `romance`
- `sad_emotional`
- `feel_good`
- `funny`
- `dark_intense`
- `reference`
- `narrative`
- `use_case`
- `mixed`

Run the benchmark from the backend directory:

```bash
cd backend
python -m app.eval.evaluate_recommendations
```

Optional JSON report:

```bash
cd backend
python -m app.eval.evaluate_recommendations --report-file eval-report.json
```

What the benchmark prints:

- overall average score
- average by family
- worst prompts
- best prompts
- top failure reasons

How to read the scores:

- `family_match_score` checks whether `Best Match` stays inside the intended family lane.
- `genre_alignment_score` checks expected vs discouraged genre leakage.
- `mood_alignment_score` checks for emotional and tonal cues in returned text.
- `narrative_alignment_score` checks for ending and story-outcome alignment.
- `mismatch_penalty_score` pushes scores down when unrelated or discouraged content dominates.
- `overall_score` combines those lightweight heuristic signals into a single benchmark value.

Use this harness after parser, ranking, filtering, embedding, or fallback changes to catch regressions such as:

- `love movie` drifting into action or crime
- `movie to cry to` filling with comedy or sci-fi noise
- `like Interstellar but less confusing` returning animation or unrelated family titles
- `movie where the villain wins` being dominated by upbeat family-safe results

## Personalization

- The backend creates a simple `user_preferences` table automatically on startup.
- Preferences are used as a final reranking layer after TMDB retrieval and optional embedding reranking.
- If no preferences exist for a user, recommendation behavior stays the same as before.
- Guest users can still request recommendations without signing in.
- Signed-in users get account-linked preferences, watchlist items, watched history, and thumbs feedback persistence.
- Session auth uses an HTTP-only cookie set by the backend auth endpoints.
- Recommendations automatically use saved account preferences when a user is authenticated.

## Production Deployment

Target setup:

- Frontend on Vercel
- Backend web service on Render
- PostgreSQL on Render

### Production Readiness Review

This repo is now prepared for that split deployment:

- Backend CORS supports explicit origin lists through `FRONTEND_ORIGINS`.
- Backend also supports `FRONTEND_ORIGIN_REGEX` for Vercel preview URLs if you want preview auth/testing.
- Session cookies are configurable for production with:
  - `AUTH_COOKIE_SECURE`
  - `AUTH_COOKIE_SAMESITE`
  - `AUTH_COOKIE_DOMAIN`
- `DATABASE_URL` is normalized for SQLAlchemy, so Render-style `postgres://...` and `postgresql://...` values both work.
- Health check path is `GET /api/v1/health`.
- Frontend API calls already use `NEXT_PUBLIC_API_BASE_URL` and `credentials: "include"`.
- Local development remains unchanged because the default cookie settings stay `secure=false` and `samesite=lax`.

### Backend Env For Render

Use these values in the Render backend service:

```env
APP_ENV=production
DATABASE_URL=<Render PostgreSQL internal database URL>
FRONTEND_ORIGIN=https://<your-vercel-production-domain>
FRONTEND_ORIGINS=http://localhost:3000,https://<your-vercel-production-domain>
FRONTEND_ORIGIN_REGEX=https://.*\.vercel\.app
TMDB_API_KEY=<your TMDB bearer token>
TMDB_BASE_URL=https://api.themoviedb.org/3
TMDB_IMAGE_BASE_URL=https://image.tmdb.org/t/p/w500
OPENAI_API_KEY=<optional>
OPENAI_MODEL=gpt-5.4-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=512
AUTH_COOKIE_NAME=movie_reco_session
AUTH_SESSION_HOURS=168
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=none
AUTH_COOKIE_DOMAIN=
```

Notes:

- Leave `AUTH_COOKIE_DOMAIN` empty unless you later move the backend behind a custom shared domain and know you need it.
- If you do not want Vercel preview deployments to call the backend, leave `FRONTEND_ORIGIN_REGEX` empty and only use your production frontend domain in `FRONTEND_ORIGINS`.

### Frontend Env For Vercel

Set this in the Vercel project:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-render-backend-domain>
```

### Manual Steps In Render

1. Create a new PostgreSQL instance in Render.
2. Copy the database's internal connection string.
3. Create a new Web Service from this repo.
4. Set the Root Directory to `backend`.
5. Set the Build Command to:

```bash
pip install -r requirements.txt
```

6. Set the Start Command to:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

7. Add the backend environment variables listed above.
8. Set the Health Check Path to:

```text
/api/v1/health
```

9. Deploy once.
10. Copy the public backend URL after deploy succeeds.

### Manual Steps In Vercel

1. Import this repo as a new Vercel project.
2. Set the Root Directory to `frontend`.
3. Keep the framework preset as Next.js.
4. Add:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-render-backend-domain>
```

5. Deploy.
6. Copy the production frontend URL.
7. Go back to Render and update:
   - `FRONTEND_ORIGIN`
   - `FRONTEND_ORIGINS`
   - optionally `FRONTEND_ORIGIN_REGEX`
8. Redeploy the Render backend so the new CORS settings take effect.

### Deployment Checklist

- Render PostgreSQL created
- Render backend service created with Root Directory `backend`
- Render backend health check set to `/api/v1/health`
- Render backend env vars set, especially `DATABASE_URL`, `TMDB_API_KEY`, `FRONTEND_ORIGINS`, `AUTH_COOKIE_SECURE=true`, and `AUTH_COOKIE_SAMESITE=none`
- Vercel frontend project created with Root Directory `frontend`
- Vercel env var `NEXT_PUBLIC_API_BASE_URL` set to the Render backend URL
- Backend CORS includes the Vercel production domain
- Optional: backend `FRONTEND_ORIGIN_REGEX` set if you want Vercel preview URLs to work
- Sign up / login tested in production
- Watchlist / preferences tested in production
- Recommendation request tested in production

### What You Must Do Manually

You still need to do these steps yourself in the provider dashboards:

- Create the Render PostgreSQL database
- Create the Render web service and paste the env vars
- Set Render's health check path and start command
- Create the Vercel project and set `NEXT_PUBLIC_API_BASE_URL`
- Copy the final Vercel production URL into Render CORS settings
- Redeploy the backend after the final frontend URL is known

## Exact Commands

Run backend:

```bash
cd backend
python -m pip install --user -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Run frontend in a new terminal:

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Test recommendations:

```bash
curl -X POST http://localhost:8000/api/v1/recommendations ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"dark sci-fi thrillers with strong visuals\"}"
```
