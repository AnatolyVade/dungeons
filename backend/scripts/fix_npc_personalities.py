"""One-time fix: add personality and backstory to existing NPCs."""
import sys
sys.path.insert(0, "/opt/projects/dungeons/backend")

from app.core.supabase import get_supabase_client

db = get_supabase_client()

CAMPAIGN_ID = "b0cfb5d7-2bb8-46dc-a94f-1b77a1f6c039"

fixes = {
    "Старый Мастер Корней": {
        "personality": "Мудрый старый мастер-ремесленник, деревенский старейшина. Знает все о деревне и окрестностях.",
        "backstory": "Живет в Ивовке всю жизнь, был мастером на все руки. Теперь стар, но уважаем всеми в деревне как мудрый наставник.",
    },
    "Матушка Агафья": {
        "personality": "Добрая пожилая женщина, деревенская целительница и хранительница народных традиций.",
        "backstory": "Травница и знахарка, лечит жителей Ивовки народными средствами. Знает старые предания и легенды края.",
    },
    "Бабка Дарья - знахарка": {
        "personality": "Опытная знахарка, знаток трав и народной магии. Мудрая, но требует уважения.",
        "backstory": "Всю жизнь изучала свойства трав и народные обряды. Может научить травничеству и приготовлению отваров.",
    },
    "Кузнец Иван": {
        "personality": "Сильный молчаливый кузнец. Искусный мастер, делает лучшее оружие и доспехи в округе.",
        "backstory": "Кузнец Ивовки, работает в деревенской кузнице. Торгует оружием и доспехами собственного производства.",
    },
    "Знахарка Дарья": {
        "personality": "Деревенская знахарка, знаток трав и целебных отваров.",
        "backstory": "Собирает травы в окрестных лесах, готовит лечебные снадобья для жителей деревни.",
    },
}

npcs = db.table("npcs").select("id, name_ru").eq("campaign_id", CAMPAIGN_ID).execute().data
for npc in npcs:
    if npc["name_ru"] in fixes:
        fix = fixes[npc["name_ru"]]
        db.table("npcs").update(fix).eq("id", npc["id"]).execute()
        print(f"Fixed: {npc['name_ru']}")
    else:
        print(f"No fix for: {npc['name_ru']}")

print("Done")
