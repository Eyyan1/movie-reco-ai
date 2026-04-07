"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, UserRound } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

export function AccountMenu() {
  const router = useRouter();
  const { user, logout, isLoading } = useAuth();

  const handleLogout = async () => {
    await logout();
    router.push("/");
    router.refresh();
  };

  if (isLoading) {
    return (
      <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300">
        Loading account...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Button asChild variant="outline" className="rounded-full border-white/10 bg-white/5 text-white">
          <Link href="/login">
            Sign in
          </Link>
        </Button>
        <Button asChild className="rounded-full">
          <Link href="/signup">
            Create account
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Button asChild variant="outline" className="rounded-full border-white/10 bg-white/5 text-white">
        <Link href="/watchlist">
          Watchlist
        </Link>
      </Button>
      <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/90">
        <UserRound className="size-4 text-primary" />
        <span className="max-w-40 truncate">{user.email}</span>
      </div>
      <Button
        type="button"
        variant="ghost"
        className="rounded-full text-white/80 hover:bg-white/10"
        onClick={handleLogout}
      >
        <LogOut className="size-4" />
      </Button>
    </div>
  );
}
