"use client";

import { useState } from "react";
import Link from "next/link";
import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

type AuthFormProps = {
  mode: "login" | "signup";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const { login, signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const isSignup = mode === "signup";

  const handleSubmit = async () => {
    setError(null);
    setIsLoading(true);
    try {
      if (isSignup) {
        await signUp({ email, password });
      } else {
        await login({ email, password });
      }
      router.push("/");
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to authenticate right now."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen px-6 py-12 md:px-10 lg:px-16">
      <div className="mx-auto flex max-w-5xl items-center justify-center">
        <div className="w-full max-w-md rounded-[2rem] border border-white/10 bg-black/35 p-8 backdrop-blur-xl">
          <p className="text-xs uppercase tracking-[0.35em] text-muted-foreground">
            {isSignup ? "Create Account" : "Sign In"}
          </p>
          <h1 className="mt-3 text-4xl font-semibold text-white">
            {isSignup ? "Save your movie taste" : "Welcome back"}
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-300">
            {isSignup
              ? "Create an account to persist preferences, watchlist picks, and watched history."
              : "Sign in to sync your taste profile, watchlist, and watched history."}
          </p>

          <div className="mt-8 flex flex-col gap-4">
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="h-12 rounded-2xl border border-white/10 bg-black/30 px-4 text-sm text-white outline-none"
            />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 characters"
              className="h-12 rounded-2xl border border-white/10 bg-black/30 px-4 text-sm text-white outline-none"
            />
            {error ? (
              <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            ) : null}
            <Button onClick={handleSubmit} disabled={isLoading} className="rounded-full">
              {isLoading ? <LoaderCircle className="animate-spin" /> : null}
              {isSignup ? "Create account" : "Sign in"}
            </Button>
          </div>

          <p className="mt-6 text-sm text-slate-400">
            {isSignup ? "Already have an account?" : "Need an account?"}{" "}
            <Link
              href={isSignup ? "/login" : "/signup"}
              className="text-white underline decoration-primary/60 underline-offset-4"
            >
              {isSignup ? "Sign in" : "Create one"}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
