"""
Fetch real travel content from Wikivoyage and write rag_documents/destinations.json.

Run from backend/:
    python -m scripts.fetch_wikivoyage

Uses the Wikivoyage MediaWiki API (free, no key required).
Each destination produces two documents:
  - overview        : Understand + Get in sections
  - practical_guide : Do + Buy + Eat + Sleep sections
"""

import json
import re
import time
from pathlib import Path

import httpx

# ── Output path ────────────────────────────────────────────────────────────────
OUT_PATH = Path(__file__).parent.parent / "rag_documents" / "destinations.json"
OUT_PATH.parent.mkdir(exist_ok=True)

API_URL = "https://en.wikivoyage.org/w/api.php"

# ── Destination metadata ───────────────────────────────────────────────────────
# wikivoyage_title: exact article title on en.wikivoyage.org
DESTINATIONS = [
    {
        "destination": "Queenstown",
        "wikivoyage_title": "Queenstown (New Zealand)",
        "country": "New Zealand",
        "travel_style": "Adventure",
        "avg_cost_per_day": 180,
        "family_friendly": False,
    },
    {
        "destination": "Patagonia",
        "wikivoyage_title": "Patagonia",
        "country": "Argentina",
        "travel_style": "Adventure",
        "avg_cost_per_day": 90,
        "family_friendly": False,
    },
    {
        "destination": "Bali",
        "wikivoyage_title": "Bali",
        "country": "Indonesia",
        "travel_style": "Relaxation",
        "avg_cost_per_day": 65,
        "family_friendly": True,
    },
    {
        "destination": "Santorini",
        "wikivoyage_title": "Santorini",
        "country": "Greece",
        "travel_style": "Relaxation",
        "avg_cost_per_day": 220,
        "family_friendly": False,
    },
    {
        "destination": "Kyoto",
        "wikivoyage_title": "Kyoto",
        "country": "Japan",
        "travel_style": "Culture",
        "avg_cost_per_day": 130,
        "family_friendly": True,
    },
    {
        "destination": "Florence",
        "wikivoyage_title": "Florence",
        "country": "Italy",
        "travel_style": "Culture",
        "avg_cost_per_day": 160,
        "family_friendly": True,
    },
    {
        "destination": "Bangkok",
        "wikivoyage_title": "Bangkok",
        "country": "Thailand",
        "travel_style": "Budget",
        "avg_cost_per_day": 40,
        "family_friendly": True,
    },
    {
        "destination": "Lisbon",
        "wikivoyage_title": "Lisbon",
        "country": "Portugal",
        "travel_style": "Budget",
        "avg_cost_per_day": 75,
        "family_friendly": True,
    },
    {
        "destination": "Dubai",
        "wikivoyage_title": "Dubai",
        "country": "UAE",
        "travel_style": "Luxury",
        "avg_cost_per_day": 400,
        "family_friendly": True,
    },
    {
        "destination": "Maldives",
        "wikivoyage_title": "Maldives",
        "country": "Maldives",
        "travel_style": "Luxury",
        "avg_cost_per_day": 650,
        "family_friendly": False,
    },
    {
        "destination": "Orlando",
        "wikivoyage_title": "Orlando",
        "country": "USA",
        "travel_style": "Family",
        "avg_cost_per_day": 200,
        "family_friendly": True,
    },
    {
        "destination": "Singapore",
        "wikivoyage_title": "Singapore",
        "country": "Singapore",
        "travel_style": "Family",
        "avg_cost_per_day": 180,
        "family_friendly": True,
    },
    {
        "destination": "Costa Rica",
        "wikivoyage_title": "Costa Rica",
        "country": "Costa Rica",
        "travel_style": "Adventure",
        "avg_cost_per_day": 100,
        "family_friendly": True,
    },
    {
        "destination": "Marrakech",
        "wikivoyage_title": "Marrakech",
        "country": "Morocco",
        "travel_style": "Culture",
        "avg_cost_per_day": 55,
        "family_friendly": True,
    },
    {
        "destination": "Phuket",
        "wikivoyage_title": "Phuket",
        "country": "Thailand",
        "travel_style": "Relaxation",
        "avg_cost_per_day": 80,
        "family_friendly": True,
    },
]

# Only sections relevant to building a travel plan
# understand → destination vibe and who it suits
# get in     → accessibility and flight cost signals
# do         → key activities (defines travel style)
# eat        → budget indicator and food culture
# sleep      → accommodation price range
KEPT_SECTIONS = {"understand", "get in", "do", "eat", "sleep"}

SECTION_LABELS = {
    "understand": "understand",
    "get in": "get_in",
    "do": "do",
    "eat": "eat",
    "sleep": "sleep",
}

# Minimum characters a section must have to be worth storing
MIN_SECTION_LENGTH = 80


def fetch_sections(title: str, client: httpx.Client) -> dict[str, str]:
    """
    Call Wikivoyage API and return a dict of {section_title_lower: plain_text}.
    Uses prop=revisions to get wikitext, then strips markup ourselves so we
    can split on == Headings == cleanly.
    """
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json",
    }
    resp = client.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        print(f"  WARNING: article not found for '{title}'")
        return {}

    wikitext: str = pages[0]["revisions"][0]["slots"]["main"]["content"]
    return parse_sections(wikitext)


def parse_sections(wikitext: str) -> dict[str, str]:
    """
    Split wikitext by == Section == headings.
    Returns {heading_lower: cleaned_text} with basic markup stripped.
    """
    # Match == Heading == (level 2) or === Heading === (level 3)
    pattern = re.compile(r"^={2,3}\s*(.+?)\s*={2,3}\s*$", re.MULTILINE)
    splits = list(pattern.finditer(wikitext))

    sections: dict[str, str] = {}

    # Text before the first heading → "intro"
    intro_end = splits[0].start() if splits else len(wikitext)
    sections["intro"] = clean(wikitext[:intro_end])

    for i, match in enumerate(splits):
        heading = match.group(1).strip().lower()
        start = match.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(wikitext)
        sections[heading] = clean(wikitext[start:end])

    return sections


def clean(text: str) -> str:
    """Strip common wikitext markup, leaving readable plain text."""
    # Remove templates {{...}}
    text = re.sub(r"\{\{[^}]*\}\}", " ", text)
    # Remove [[File:...]] and [[Image:...]]
    text = re.sub(r"\[\[(File|Image):[^\]]*\]\]", " ", text, flags=re.IGNORECASE)
    # Convert [[link|display]] → display, [[link]] → link
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # Remove external links [url text] → text
    text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\]", " ", text)
    # Remove bold/italic markers
    text = re.sub(r"'{2,3}", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def build_documents(dest: dict, sections: dict[str, str]) -> list[dict]:
    """
    One document per Wikivoyage section.
    A destination with 8 sections → 8 rows in the DB.
    Each row covers exactly one topic (eat, sleep, do etc.)
    so similarity search returns precisely relevant content.
    """
    slug = dest["destination"].lower().replace(" ", "-")
    base = {
        "destination": dest["destination"],
        "country": dest["country"],
        "travel_style": dest["travel_style"],
        "avg_cost_per_day": dest["avg_cost_per_day"],
        "family_friendly": dest["family_friendly"],
        "source": f"Wikivoyage – {dest['wikivoyage_title']}",
    }

    docs = []
    for section_key, text in sections.items():
        # Skip sections we don't care about or that are too short to be useful
        if section_key not in KEPT_SECTIONS:
            continue
        if len(text.strip()) < MIN_SECTION_LENGTH:
            continue

        doc_type = SECTION_LABELS.get(section_key, section_key.replace(" ", "_"))

        # Prefix content with the section name so the embedding captures the topic
        content = f"{section_key.title()}\n{text.strip()}"

        docs.append({
            "id": f"{slug}-{doc_type}",
            "doc_type": doc_type,
            "content": content,
            **base,
        })

    # Fallback: if no kept sections found, store whatever text exists
    if not docs:
        fallback = sections.get("understand") or sections.get("intro") or ""
        if fallback.strip():
            docs.append({
                "id": f"{slug}-understand",
                "doc_type": "understand",
                "content": fallback.strip(),
                **base,
            })

    return docs


def main() -> None:
    documents: list[dict] = []

    with httpx.Client(headers={"User-Agent": "TravelPlannerRAG/1.0 (educational)"}) as client:
        for dest in DESTINATIONS:
            print(f"Fetching: {dest['wikivoyage_title']} ...")
            try:
                sections = fetch_sections(dest["wikivoyage_title"], client)
                docs = build_documents(dest, sections)
                documents.extend(docs)
                print(f"  ✓ {len(docs)} docs | sections found: {list(sections.keys())[:6]}")
            except Exception as exc:
                print(f"  ERROR: {exc}")

            # Be polite to the API — 1 req/sec
            time.sleep(1)

    OUT_PATH.write_text(json.dumps(documents, indent=2, ensure_ascii=False))
    print(f"\nWrote {len(documents)} documents → {OUT_PATH}")


if __name__ == "__main__":
    main()
