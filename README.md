# Wildtrack

The sister of Talkback, for people who make sound. In film sound, a wildtrack is sound recorded without picture, free to become anything. It covers sound design, composition, field recording, sound art and every craft that meets audio.
Every morning: one seed taken from the real world (a photograph, a quotation, a concept or a word, always with its source), something to listen to, a lesson from another profession, and 14–22 verified news stories.

It's a static site built the same way as Talkback: one `index.html`, a few images, and JSON files in `data/`. No build step, no server, no accounts.

## Deploy on GitHub Pages (once)

1. Create a new **public** repository on GitHub, e.g. `wildtrack`, without a README.
2. Upload everything in this folder (or push it with git, see below), keeping the folder structure, including the hidden `.github` folder and `.nojekyll`.
3. In the repo go to **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
4. Open the **Actions** tab. The "Deploy to GitHub Pages" workflow runs on every push. When it's green, your site is live at
   `https://<your-username>.github.io/wildtrack/`

With git from a terminal:

```bash
cd wildtrack-site
git init -b main
git add .
git commit -m "Wildtrack first release"
git remote add origin https://github.com/<your-username>/wildtrack.git
git push -u origin main
```

### Custom domain: wildtrack.danielbovolon.com

Do these in order (it's the same setup as talkback.danielbovolon.com):

1. **Verify the domain on GitHub (once per domain).** If you already verified `danielbovolon.com` for Talkback, skip this. Otherwise go to your GitHub profile **Settings → Pages → Add a domain**, enter `danielbovolon.com`, and add the TXT record GitHub shows you at your DNS provider. This stops anyone else from claiming your subdomains.
2. **Add the domain to the repo.** In the `wildtrack` repo go to **Settings → Pages → Custom domain**, enter `wildtrack.danielbovolon.com` and click **Save**.
3. **Add the CNAME record** at your DNS provider (where `danielbovolon.com` is managed):

   | Type | Name / Host | Value / Target | TTL |
   | --- | --- | --- | --- |
   | CNAME | `wildtrack` | `<your-github-username>.github.io` | default / 3600 |

   Use exactly the same target as your existing `talkback` record. Don't add the repo name to the target, and don't add `https://`. Some providers want the full name (`wildtrack.danielbovolon.com.`) in the Name field.
4. **Wait for the check.** Back in **Settings → Pages**, GitHub shows "DNS check successful" once the record is live (minutes to a few hours). Then tick **Enforce HTTPS**.

No `CNAME` file is needed in this repo: the site is published with a GitHub Actions workflow, and GitHub ignores CNAME files in that case. The domain lives in the repo settings.

To check from a terminal: `nslookup wildtrack.danielbovolon.com` should show `<your-github-username>.github.io`.

## Daily updates

New content is just one new JSON file a day:

- `data/seeds/seed-YYYY-MM-DD.json`

Commit it to `main`. The workflow validates every file, rebuilds `data/index.json` and redeploys. If a file is malformed the deploy fails and the live site keeps the previous version.

To preview locally:

```bash
python3 scripts/build_index.py
python3 -m http.server 8000
# open http://localhost:8000
```

(Opening `index.html` directly from disk won't load the data; browsers block that. Use the local server.)

## What's where

| Path | What it is |
| --- | --- |
| `index.html` | The whole app: layout, styles and code |
| `assets/` | Logo, app icons, favicon, social preview image |
| `manifest.webmanifest` | Lets people add Wildtrack to their home screen as an app |
| `data/` | Daily seeds and the generated `index.json` |
| `scripts/build_index.py` | Validates data and rebuilds the index |
| `.github/workflows/pages.yml` | Automatic deploy to GitHub Pages |

## Seed file format

Each `seed-YYYY-MM-DD.json` holds `key`, `label`, `range`, `generated`, `seed`, `visual`, `listen`, `crossover`, `headline`, `lead`, `items` and `radar`. See `data/seeds/seed-2026-10-04.json` for a complete example.

The `seed` is always real material with a source, never invented:

- `kind`: `photo`, `quote`, `concept` or `word`
- `text`: the photo's subject, the quotation, the term or the word
- `note`: a short factual note
- `source`: `{ label, url }` (required except for photos)
- `by`, `work`, `year`: who said or wrote a quotation
- `lang`: language of a foreign word
- `photo`: `{ src, title, alt, credit, licence, page }`, for example from Wikimedia Commons; `page` links to where the photo and its licence are shown

`visual` describes the generated pattern shown when there is no photo (or when a viewer can't load it).

Sections for `items[].cat`: `sounddesign`, `music`, `field`, `synthesis`, `tools`, `film`, `games`, `art`, `space`, `stage`, `radio`, `visual`, `design`, `nature`, `access`, `calls`.

## Personalising

- **About text** is in the `<footer class="about">` block near the top of `index.html`. Add your name, Instagram handle or website there.
- **Social preview** (the image Instagram and WhatsApp show for links) is `assets/og-image.png`.

## Privacy

There's no tracking and no sign-in. Pins, the journal, the last-opened tab and the "made something" log are stored only in each visitor's browser.
