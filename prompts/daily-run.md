# Daily Run Prompt

Use this workflow each morning:

1. Determine today's date in Romania time.
2. Research the day's biggest stories from credible major outlets. Prioritize Reuters, AP, NPR, BBC, Al Jazeera, CNN, NASA, official institutions, and similarly credible primary reporting. Also check Reddit for a few genuinely interesting trending posts.
3. Select the 15-20 stories that best help a reader understand what is happening in the world that morning. Do not force a fixed topic list. Let the day's news decide the sections.
4. Group stories into natural sections after research. Use concise section names such as `Middle East Crisis`, `Ukraine War`, `Markets & Energy`, `Science`, `U.S. Politics`, `Elections`, `Tech`, or whatever is actually justified that day. Recurring topics like conflict, economy, space, climate, and diplomacy are welcome when important, but should not appear just to fill a quota.
5. Keep `Romania` as a dedicated section when there are meaningful Romania stories, and keep `Trending on Reddit` as a dedicated section when Reddit adds real public-signal value. If either lane has no meaningful signal, say so in `summary.reader_note` rather than padding with weak stories.
6. Create `content/YYYY-MM-DD.json` by copying `content/_edition-template.json` and filling it with real stories, links, countries, summaries, and why-it-matters notes. Each section should include a stable lowercase `key`, a user-facing `title`, a one-sentence `description`, an optional `kicker`, and an optional `tone`.
7. Keep the writing concise, skimmable, and sourced, but always write complete sentences and complete thoughts. Do not end summaries or `why_it_matters` fields with `...`, clipped fragments, or unfinished ideas. If space is tight, rewrite the sentence cleanly instead of truncating it.
8. Add images only when they materially improve understanding and you can verify a stable direct image URL from a credible source or official institution. Prefer one image for the featured story and at most a few images across the rest of the edition. Keep `image.alt` plain, factual, and useful; include `image.credit` when it is clearly available. If the image URL is uncertain, omit the image instead of guessing.
9. Run `python scripts/build_site.py`.
10. Review the generated `docs/` output for obvious layout issues, including broken images, awkward crops, or clipped text.
11. Run `pwsh -File scripts/publish.ps1`.

Important constraints:

- Always keep both the dated edition and the stable `latest/` output.
- Do not remove older dated editions.
- If there is already a file for today, update it instead of creating a duplicate.
- If there are no content changes worth publishing, stop before committing.
- Valid section tones are `conflict`, `ukraine`, `diplomacy`, `policy`, `economy`, `space`, `environment`, `romania`, and `reddit`; omit `tone` for other natural sections and the builder will assign a readable automatic accent.
- Images are optional. Never invent image URLs, never use obvious placeholders, and never force an image into every story.
