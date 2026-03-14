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
    <main className="flex items-center justify-center min-h-screen px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-gray-900 p-8 rounded-xl border border-gray-800"
      >
        <h1 className="text-2xl font-bold mb-6 text-[var(--color-gold)]">
          Login
        </h1>

        {error && (
          <p className="text-red-400 text-sm mb-4">{error}</p>
        )}

        <label className="block mb-4">
          <span className="text-sm text-gray-400">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-[var(--color-gold)]"
          />
        </label>

        <label className="block mb-6">
          <span className="text-sm text-gray-400">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-[var(--color-gold)]"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-[var(--color-gold)] text-gray-950 font-semibold rounded-lg hover:brightness-110 transition disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Login"}
        </button>

        <p className="mt-4 text-sm text-gray-500 text-center">
          No account?{" "}
          <Link href="/auth/register" className="text-[var(--color-gold)] hover:underline">
            Register
          </Link>
        </p>
      </form>
    </main>
  );
}
