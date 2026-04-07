from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
SITE_DIR = ROOT / "site"
DOCS_DIR = ROOT / "docs"
ASSETS_DIR = DOCS_DIR / "assets"
DATE_FMT = "%Y-%m-%d"

SECTION_META = {
    "conflict": {"title": "Conflict & Geopolitics", "description": "Major flashpoints, military escalation, and regional pressure points.", "icon": "Crosswinds", "tone": "tone-conflict"},
    "ukraine": {"title": "Ukraine-Russia War", "description": "Front-line movement, strikes, and strategic infrastructure pressure.", "icon": "Eastern Front", "tone": "tone-ukraine"},
    "diplomacy": {"title": "Diplomacy", "description": "Signals from mediators, negotiations, and international positioning.", "icon": "Statecraft", "tone": "tone-diplomacy"},
    "policy": {"title": "U.S. Policy", "description": "Decisions in Washington with broad global spillover.", "icon": "Policy Lens", "tone": "tone-policy"},
    "economy": {"title": "Economy & Energy", "description": "Markets, oil, inflation pressure, and the business implications of global events.", "icon": "Market Pulse", "tone": "tone-economy"},
    "space": {"title": "Space & Science", "description": "High-signal research, exploration, and scientific milestones.", "icon": "Deep Sky", "tone": "tone-space"},
    "environment": {"title": "Climate & Environment", "description": "Weather extremes, long-term climate shifts, and the energy transition.", "icon": "Green Horizon", "tone": "tone-environment"},
    "romania": {"title": "Romania", "description": "The domestic stories most likely to matter locally.", "icon": "Local Focus", "tone": "tone-romania"},
    "reddit": {"title": "Trending on Reddit", "description": "A few conversation-led signals that surfaced outside traditional outlets.", "icon": "Public Signal", "tone": "tone-reddit"},
}

TONE_KEYS = (
    "conflict",
    "ukraine",
    "diplomacy",
    "policy",
    "economy",
    "space",
    "environment",
    "romania",
    "reddit",
)

AUTO_TONES = (
    "tone-auto-1",
    "tone-auto-2",
    "tone-auto-3",
    "tone-auto-4",
    "tone-auto-5",
    "tone-auto-6",
    "tone-auto-7",
    "tone-auto-8",
)


def load_template(name: str) -> str:
    return (SITE_DIR / name).read_text(encoding="utf-8")


def format_long_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, DATE_FMT)
    return dt.strftime("%A, %B %d, %Y")


def format_generated_at(value: str) -> str:
    dt = datetime.fromisoformat(value)
    return dt.strftime("%B %d, %Y at %H:%M")


def read_editions() -> list[dict]:
    editions = []
    for path in sorted(CONTENT_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        editions.append(data)
    editions.sort(key=lambda item: item["date"], reverse=True)
    return editions


def collect_stats(edition: dict) -> dict:
    stories = [edition["featured_story"]]
    for section in edition["sections"]:
        stories.extend(section["stories"])

    source_names = set()
    countries = set()
    for story in stories:
        for source in story.get("sources", []):
            source_names.add(source["name"])
        for country in story.get("countries", []):
            countries.add(country)

    return {
        "stories": len(stories),
        "categories": len([section for section in edition["sections"] if section.get("stories")]),
        "countries": len(countries),
        "sources": len(source_names),
    }


def render_sources(sources: list[dict]) -> str:
    links = []
    for source in sources:
        links.append(
            f'<a href="{escape(source["url"], quote=True)}" target="_blank" rel="noreferrer">{escape(source["name"])}</a>'
        )
    return " · ".join(links)


def titleize_key(key: str) -> str:
    return key.replace("-", " ").replace("_", " ").title()


def normalize_tone(value: str | None) -> str | None:
    if not value:
        return None
    tone = value.removeprefix("tone-").lower().strip()
    if tone in TONE_KEYS:
        return f"tone-{tone}"
    auto_tone = f"tone-{tone}"
    if auto_tone in AUTO_TONES:
        return auto_tone
    return None


def section_meta(section: dict, index: int) -> dict:
    key = section["key"]
    known = SECTION_META.get(key, {})
    tone = normalize_tone(section.get("tone")) or known.get("tone") or AUTO_TONES[index % len(AUTO_TONES)]
    return {
        "title": section.get("title") or known.get("title") or titleize_key(key),
        "description": section.get("description") or known.get("description") or "The day's most relevant stories in this lane.",
        "icon": section.get("kicker") or section.get("icon") or known.get("icon") or "Briefing",
        "tone": tone,
    }


def section_tones(edition: dict) -> dict[str, str]:
    return {
        section["key"]: section_meta(section, index)["tone"]
        for index, section in enumerate(edition["sections"])
        if section.get("stories")
    }


def render_story(section_key: str, story: dict, tone: str) -> str:
    countries = ", ".join(escape(country) for country in story.get("countries", []))
    meta_bits = [f'<span class="story-meta-item">{countries}</span>'] if countries else []
    if story.get("score"):
        meta_bits.append(f'<span class="story-meta-item">▲ {escape(story["score"])}</span>')
    if story.get("comments"):
        meta_bits.append(f'<span class="story-meta-item">{escape(story["comments"])} comments</span>')
    meta = "".join(meta_bits)
    return f"""
      <article class="story-card {escape(tone)}" data-category="{escape(section_key)}">
        <div class="story-card-head">
          <span class="story-pill">{escape(story["label"])}</span>
        </div>
        <h3>{escape(story["headline"])}</h3>
        <p class="story-summary">{escape(story["summary"])}</p>
        <p class="story-why"><strong>Why it matters:</strong> {escape(story["why_it_matters"])}</p>
        <div class="story-meta">{meta}</div>
        <div class="story-sources">{render_sources(story.get("sources", []))}</div>
      </article>
    """.strip()


def render_section(section: dict, index: int) -> str:
    section_key = section["key"]
    meta = section_meta(section, index)
    cards = "\n".join(render_story(section_key, story, meta["tone"]) for story in section.get("stories", []))
    count = len(section.get("stories", []))
    story_label = "story" if count == 1 else "stories"
    return f"""
    <section class="news-section" data-section="{escape(section_key)}">
      <div class="section-frame {escape(meta["tone"])}">
        <div class="section-topline">
          <div>
            <p class="section-kicker">{escape(meta["icon"])}</p>
            <h2>{escape(meta["title"])}</h2>
          </div>
          <span class="section-count">{count} {story_label}</span>
        </div>
        <p class="section-description">{escape(meta["description"])}</p>
        <div class="story-grid">
          {cards}
        </div>
      </div>
    </section>
    """.strip()


def render_featured(edition: dict, tones: dict[str, str]) -> str:
    story = edition["featured_story"]
    category = story.get("category", "conflict")
    tone = normalize_tone(story.get("tone")) or tones.get(category) or normalize_tone(category) or "tone-default"
    countries = ", ".join(escape(country) for country in story.get("countries", []))
    return f"""
    <section class="featured-wrap" data-section="featured">
      <article class="featured-card {escape(tone)}" data-category="{escape(category)}">
        <div class="featured-head">
          <span class="story-pill">{escape(story["label"])}</span>
          <span class="featured-countries">{countries}</span>
        </div>
        <h2>{escape(story["headline"])}</h2>
        <p class="featured-summary">{escape(story["summary"])}</p>
        <p class="featured-why"><strong>Why it matters:</strong> {escape(story["why_it_matters"])}</p>
        <div class="story-sources">{render_sources(story.get("sources", []))}</div>
      </article>
    </section>
    """.strip()


def render_filter_pills(edition: dict) -> str:
    pills = ['<button class="filter-pill is-active" data-filter="all" type="button">All</button>']
    for index, section in enumerate(edition["sections"]):
        stories = section.get("stories", [])
        if not stories:
            continue
        key = section["key"]
        meta = section_meta(section, index)
        title = escape(meta["title"])
        pills.append(f'<button class="filter-pill {escape(meta["tone"])}" data-filter="{escape(key)}" type="button">{title} <span>{len(stories)}</span></button>')
    return "\n".join(pills)


def render_stats(edition: dict) -> str:
    stats = collect_stats(edition)
    items = [("Stories", str(stats["stories"])), ("Sections", str(stats["categories"])), ("Countries", str(stats["countries"])), ("Sources", str(stats["sources"]))]
    return "\n".join(
        f"""
        <div class="stat-card">
          <div class="stat-value">{escape(value)}</div>
          <div class="stat-label">{escape(label)}</div>
        </div>
        """.strip()
        for label, value in items
    )


def render_page(edition: dict, asset_prefix: str, archive_href: str, latest_href: str) -> str:
    template = load_template("template.html")
    tones = section_tones(edition)
    sections = "\n".join(render_section(section, index) for index, section in enumerate(edition["sections"]) if section.get("stories"))
    replacements = {
        "{{ASSET_PREFIX}}": asset_prefix,
        "{{PAGE_TITLE}}": escape(f'{edition["edition_title"]} - {format_long_date(edition["date"])}'),
        "{{EDITION_TITLE}}": escape(edition["edition_title"]),
        "{{EDITION_KICKER}}": escape(edition.get("edition_kicker", "Morning Edition")),
        "{{EDITION_SUBTITLE}}": escape(edition.get("edition_subtitle", "")),
        "{{DATE_LONG}}": escape(format_long_date(edition["date"])),
        "{{GENERATED_AT}}": escape(format_generated_at(edition["generated_at"])),
        "{{SPOTLIGHT}}": escape(edition.get("summary", {}).get("spotlight", "")),
        "{{MARKET_MOOD}}": escape(edition.get("summary", {}).get("market_mood", "")),
        "{{READER_NOTE}}": escape(edition.get("summary", {}).get("reader_note", "")),
        "{{SUMMARY_STATS}}": render_stats(edition),
        "{{FILTER_PILLS}}": render_filter_pills(edition),
        "{{FEATURED_STORY}}": render_featured(edition, tones),
        "{{SECTIONS}}": sections,
        "{{ARCHIVE_HREF}}": archive_href,
        "{{LATEST_HREF}}": latest_href,
    }
    html = template
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def render_archive(editions: list[dict]) -> str:
    template = load_template("archive.html")
    latest = editions[0]
    archive_items = []
    for edition in editions:
        archive_items.append(
            f"""
            <a class="archive-link" href="./{escape(edition["date"])}/">
              <div>
                <div class="archive-date">{escape(format_long_date(edition["date"]))}</div>
                <div class="archive-subtitle">{escape(edition.get("edition_subtitle", ""))}</div>
              </div>
              <span class="archive-arrow">Open</span>
            </a>
            """.strip()
        )

    html = template
    for key, value in {
        "{{PAGE_TITLE}}": "Daily News Archive",
        "{{ASSET_PREFIX}}": "assets",
        "{{LATEST_DATE}}": escape(format_long_date(latest["date"])),
        "{{LATEST_SUBTITLE}}": escape(latest.get("edition_subtitle", "")),
        "{{LATEST_PATH}}": "./latest/",
        "{{ARCHIVE_ITEMS}}": "\n".join(archive_items),
        "{{LAST_UPDATED}}": escape(format_generated_at(latest["generated_at"])),
    }.items():
        html = html.replace(key, value)
    return html


def ensure_assets() -> None:
    if ASSETS_DIR.exists():
        shutil.rmtree(ASSETS_DIR)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SITE_DIR / "styles.css", ASSETS_DIR / "styles.css")
    shutil.copy2(SITE_DIR / "app.js", ASSETS_DIR / "app.js")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build() -> None:
    editions = read_editions()
    if not editions:
        raise SystemExit("No edition files found in content/.")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ensure_assets()
    write_text(DOCS_DIR / "index.html", render_archive(editions))
    write_text(DOCS_DIR / ".nojekyll", "")

    latest = editions[0]
    for edition in editions:
        date_slug = edition["date"]
        write_text(DOCS_DIR / f"{date_slug}.html", render_page(edition, "assets", "./index.html", "./latest/"))
        write_text(DOCS_DIR / date_slug / "index.html", render_page(edition, "../assets", "../index.html", "../latest/"))

    write_text(DOCS_DIR / "latest.html", render_page(latest, "assets", "./index.html", "./latest/"))
    write_text(DOCS_DIR / "latest" / "index.html", render_page(latest, "../assets", "../index.html", "./"))


if __name__ == "__main__":
    build()
