# Daily Run Prompt

Use this workflow each morning:

1. Determine today's date in Romania time.
2. Research the day's biggest stories from credible major outlets. Prioritize Reuters, AP, NPR, BBC, Al Jazeera, CNN, NASA, and similarly credible primary reporting. Also check Reddit for a few genuinely interesting trending posts.
3. Focus on these buckets:
   - Conflict & Geopolitics
   - Ukraine-Russia War
   - Diplomacy
   - U.S. Policy
   - Economy & Energy
   - Space & Science
   - Climate & Environment
   - Romania
   - Reddit
4. Aim for 15-20 total stories, with one featured story.
5. Create `content/YYYY-MM-DD.json` by copying `content/_edition-template.json` and filling it with real stories, links, countries, summaries, and why-it-matters notes.
6. Keep the writing concise, skimmable, and sourced. Prefer direct reporting over low-quality aggregation.
7. Run `python scripts/build_site.py`.
8. Review the generated `docs/` output for obvious layout issues.
9. Run `pwsh -File scripts/publish.ps1`.

Important constraints:

- Always keep both the dated edition and the stable `latest/` output.
- Do not remove older dated editions.
- If there is already a file for today, update it instead of creating a duplicate.
- If there are no content changes worth publishing, stop before committing.
