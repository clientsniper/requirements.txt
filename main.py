from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import httpx
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

KEYWORDS = {
    "barber": ["hairdresser","barber","salon"],
    "restaurant": ["restaurant","fast_food","cafe"],
    "gym": ["fitness_centre"],
    "beauty": ["beauty","nail_salon","cosmetics"]
}

def build_query(city: str, keyword: str):
    return f"""
    [out:json][timeout:20];
    area["name"="{city}"]->.a;
    (
      node["amenity"="{keyword}"](area.a);
      node["shop"="{keyword}"](area.a);
      way["amenity"="{keyword}"](area.a);
      way["shop"="{keyword}"](area.a);
    );
    out tags center 50;
    """

async def fetch_overpass(city: str, keyword: str):
    query = build_query(city, keyword)
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(OVERPASS_URL, data=query)
            data = r.json()
        except:
            return []

    leads = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        phone = tags.get("phone")
        if not name:
            continue
        leads.append({
            "name": name,
            "city": city,
            "phone": phone
        })
    return leads

@app.get("/leads")
async def get_leads(
    branchen: List[str] = Query(...),
    staedte: List[str] = Query(...)
):
    tasks = []
    for branche in branchen:
        keywords = KEYWORDS.get(branche.lower(), [branche])
        for city in staedte:
            for kw in keywords:
                tasks.append(fetch_overpass(city, kw))
    results = await asyncio.gather(*tasks)

    seen = set()
    final = []
    for sub in results:
        for l in sub:
            key = (l["name"], l["city"])
            if key not in seen:
                seen.add(key)
                final.append(l)

    return {"count": len(final), "leads": final}
