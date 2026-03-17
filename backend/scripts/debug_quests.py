"""Debug: check quests and recent chat."""
import sys
sys.path.insert(0, "/opt/projects/dungeons/backend")

from app.core.supabase import get_supabase_client
db = get_supabase_client()

CID = "b0cfb5d7-2bb8-46dc-a94f-1b77a1f6c039"

quests = db.table("quests").select("*").eq("campaign_id", CID).execute().data
print(f"=== QUESTS ({len(quests)}) ===")
for q in quests:
    title = q.get("title_ru") or q.get("title")
    print(f"  {title} | status={q['status']} | objectives={q['objectives']}")

print("\n=== LAST 10 DM MESSAGES ===")
msgs = db.table("chat_history").select("role, content, context").eq("campaign_id", CID).eq("context", "dm").order("created_at", desc=True).limit(10).execute().data
for m in reversed(msgs):
    print(f"  {m['role']}: {m['content'][:200]}")

print("\n=== LAST 6 NPC MESSAGES ===")
npc_msgs = db.table("chat_history").select("role, content, context").eq("campaign_id", CID).order("created_at", desc=True).limit(20).execute().data
npc_only = [m for m in npc_msgs if m["context"].startswith("npc_")][:6]
for m in reversed(npc_only):
    print(f"  [{m['context'][:20]}] {m['role']}: {m['content'][:200]}")
