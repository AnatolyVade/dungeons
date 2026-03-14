"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getCampaigns, createCampaign, isLoggedIn, type Campaign } from "@/lib/api";

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/auth/login");
      return;
    }
    getCampaigns().then(setCampaigns).finally(() => setLoading(false));
  }, [router]);

  async function handleCreate() {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const campaign = await createCampaign(newName.trim());
      router.push(`/campaigns/new?id=${campaign.id}`);
    } catch {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <p className="text-gray-500">Loading...</p>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8 text-[var(--color-gold)]">
        Your Campaigns
      </h1>

      {/* New Campaign */}
      <div className="mb-8 p-4 bg-gray-900 rounded-xl border border-gray-800">
        <h2 className="text-lg font-semibold mb-3">Start New Adventure</h2>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Campaign name..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-[var(--color-gold)]"
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button
            onClick={handleCreate}
            disabled={creating || !newName.trim()}
            className="px-6 py-2 bg-[var(--color-gold)] text-gray-950 font-semibold rounded-lg hover:brightness-110 transition disabled:opacity-50"
          >
            {creating ? "..." : "Create"}
          </button>
        </div>
      </div>

      {/* Campaign List */}
      {campaigns.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          No campaigns yet. Create your first adventure!
        </p>
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <Link
              key={c.id}
              href={`/play/${c.id}`}
              className="block p-4 bg-gray-900 rounded-xl border border-gray-800 hover:border-[var(--color-gold)]/50 transition"
            >
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="font-semibold text-lg">{c.name}</h3>
                  <p className="text-sm text-gray-500">
                    Turn {c.turn_count} &middot;{" "}
                    {new Date(c.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded ${
                    c.status === "active"
                      ? "bg-green-900/50 text-green-400"
                      : "bg-gray-800 text-gray-500"
                  }`}
                >
                  {c.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
