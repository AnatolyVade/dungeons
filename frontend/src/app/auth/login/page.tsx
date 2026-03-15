"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/campaigns");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex items-center justify-center min-h-screen px-4"
      style={{ background: "radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a0f 70%)" }}
    >
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold tracking-wide" style={{ color: "#d4a843" }}>
            Realms of Fate
          </h2>
          <p className="text-sm text-gray-500 mt-1">AI-Powered D&D Adventure</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-gray-900/80 backdrop-blur p-8 rounded-2xl border border-gray-800 shadow-2xl"
        >
          <h1 className="text-xl font-bold mb-6" style={{ color: "#d4a843" }}>
            Sign In
          </h1>

          {error && (
            <div className="bg-red-900/30 border border-red-800 text-red-400 text-sm px-4 py-2 rounded-lg mb-4">
              {error}
            </div>
          )}

          <label className="block mb-4">
            <span className="text-sm text-gray-400 font-medium">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="adventurer@realm.com"
              className="mt-1 w-full px-4 py-2.5 bg-gray-800/80 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-amber-700/50 focus:border-amber-700 transition"
            />
          </label>

          <label className="block mb-6">
            <span className="text-sm text-gray-400 font-medium">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="mt-1 w-full px-4 py-2.5 bg-gray-800/80 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-amber-700/50 focus:border-amber-700 transition"
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 font-semibold rounded-lg transition disabled:opacity-50 cursor-pointer"
            style={{
              background: "linear-gradient(135deg, #d4a843 0%, #b8912e 100%)",
              color: "#0a0a0f",
            }}
          >
            {loading ? "Entering the realm..." : "Enter the Realm"}
          </button>

          <p className="mt-5 text-sm text-gray-500 text-center">
            New adventurer?{" "}
            <Link href="/auth/register" className="font-medium hover:underline" style={{ color: "#d4a843" }}>
              Create Account
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
