"use client";

import Link from "next/link";
import { isLoggedIn } from "@/lib/api";
import { useEffect, useState } from "react";

export default function Home() {
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(isLoggedIn());
  }, []);

  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-4">
      <h1 className="text-6xl font-bold mb-4 text-[var(--color-gold)]">
        Realms of Fate
      </h1>
      <p className="text-xl text-gray-400 mb-12 text-center max-w-lg">
        An AI-powered open world D&amp;D adventure. Create your hero, explore
        endless worlds, and forge your own destiny.
      </p>

      <div className="flex gap-4">
        {loggedIn ? (
          <Link
            href="/campaigns"
            className="px-8 py-3 bg-[var(--color-gold)] text-gray-950 font-semibold rounded-lg hover:brightness-110 transition"
          >
            Enter the Realm
          </Link>
        ) : (
          <>
            <Link
              href="/auth/login"
              className="px-8 py-3 bg-[var(--color-gold)] text-gray-950 font-semibold rounded-lg hover:brightness-110 transition"
            >
              Login
            </Link>
            <Link
              href="/auth/register"
              className="px-8 py-3 border border-[var(--color-gold)] text-[var(--color-gold)] font-semibold rounded-lg hover:bg-[var(--color-gold)]/10 transition"
            >
              Register
            </Link>
          </>
        )}
      </div>
    </main>
  );
}
