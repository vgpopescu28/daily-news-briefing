# Daily News Briefing

This repo generates a static daily news site for GitHub Pages from structured JSON content. Each edition is archived by date and duplicated to a stable `latest/` path so you can bookmark the newest briefing.

## Structure

- `content/`: daily source files such as `2026-04-06.json`
- `site/`: HTML templates plus shared CSS and JS
- `scripts/build_site.py`: renders the static site into `docs/`
- `scripts/publish.ps1`: builds, commits, and pushes the site
- `prompts/daily-run.md`: the workflow the automation should follow each morning

## Daily Workflow

1. Research the day's stories and fill a new `content/YYYY-MM-DD.json` file.
2. Run `python scripts/build_site.py`.
3. Review the generated site in `docs/`.
4. Run `pwsh -File scripts/publish.ps1`.

## Output Layout

The build writes:

- `docs/index.html`: archive homepage
- `docs/latest/index.html`: stable latest route for GitHub Pages
- `docs/latest.html`: flat duplicate of the latest page
- `docs/YYYY-MM-DD/index.html`: dated archive route
- `docs/YYYY-MM-DD.html`: flat duplicate of the dated page

That means the bookmarkable URLs are:

- `https://<owner>.github.io/<repo>/latest/`
- `https://<owner>.github.io/<repo>/2026-04-06/`

If you later use a user site repo named `<owner>.github.io`, the URL becomes:

- `https://<owner>.github.io/latest/`

## GitHub Pages

Configure Pages to deploy from the `main` branch and the `/docs` folder.

## Content Schema

Copy `content/_edition-template.json` when creating a new edition. The builder expects:

- one `featured_story`
- one or more `sections`
- optional `summary`
- each story to include `headline`, `summary`, `why_it_matters`, `sources`, and `countries`

## Notes

- The site is fully static and works on phone, tablet, and desktop.
- The visual layout, filters, archive, and theme behavior live in templates and shared assets, so the daily automation only needs to update structured content.
