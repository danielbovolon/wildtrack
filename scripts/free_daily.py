#!/usr/bin/env python3
"""Free daily edition for Wildtrack, run by GitHub Actions (no AI, no paid services).

If today's seed (data/seeds/seed-YYYY-MM-DD.json) is missing, build one:

- seed: rotates concept / word / photo. A concept is a Wikipedia article picked from
  data/bank/concepts.json; a word is a Wiktionary entry from data/bank/words.json;
  a photo seed is a real photograph from Wikimedia Commons.
- photo: a real camera photograph from Wikimedia Commons (the concept article's own
  photo when it has one, otherwise one from a category in data/bank/photo_categories.json).
  Only JPEGs with camera EXIF data and no drawing/illustration/AI categories are used.
- poem: a short public-domain poem from PoetryDB (texts from Project Gutenberg).
- listen and crossover: Wikipedia articles picked from data/bank/listen.json and
  data/bank/crossover.json.
- items: the newest stories from the sources' news feeds (title, date, link and the
  outlet's own summary), sorted into Wildtrack's sections.

Every text in the inspiration part is copied verbatim from its source and credited with a
link. Nothing is written or generated here; the bank only holds titles to look up.
Picks rotate so nothing repeats within 30 days. Files that already exist (for example
written by a Claude run) are never touched. Only the Python standard library is used.
"""
import datetime, email.utils, hashlib, html, json, pathlib, random, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BANK = DATA / "bank"
TZ = ZoneInfo("Europe/Rome")
NOW = datetime.datetime.now(TZ)
TODAY = NOW.date()
KEY = TODAY.isoformat()
LABEL = TODAY.strftime("%a ") + str(TODAY.day) + TODAY.strftime(" %b %Y")
UA = "WildtrackFreeEdition/1.0 (https://wildtrack.danielbovolon.com; daniel.bovolon@gmail.com)"
RND = random.Random(int(hashlib.sha256(KEY.encode()).hexdigest(), 16))

# (source name, feed URL, default category, priority 1-3, only keep sound-related stories)
FEEDS = [
    ("A Sound Effect", "https://feeds.feedburner.com/ASoundEffect", "sounddesign", 3, False),
    ("Tonebenders", "https://tonebenderspodcast.com/feed/", "sounddesign", 2, False),
    ("Production Expert", "https://www.production-expert.com/production-expert-1?format=rss", "film", 2, False),
    ("CDM", "https://cdm.link/feed/", "music", 3, False),
    ("Synthtopia", "https://www.synthtopia.com/feed/", "synthesis", 2, False),
    ("Synth Anatomy", "https://synthanatomy.com/feed/", "synthesis", 2, False),
    ("Bedroom Producers Blog", "https://bedroomproducersblog.com/feed/", "tools", 2, False),
    ("Gearnews", "https://www.gearnews.com/feed/", "synthesis", 1, False),
    ("Bandcamp Daily", "https://daily.bandcamp.com/feed", "music", 2, False),
    ("The Quietus", "https://thequietus.com/feed", "music", 1, True),
    ("CreativeApplications.Net", "https://www.creativeapplications.net/feed/", "visual", 2, False),
    ("Derivative", "https://derivative.ca/rss.xml", "visual", 1, False),
    ("Dezeen (sound)", "https://www.dezeen.com/tag/sound/feed/", "space", 2, False),
    ("Hyperallergic", "https://hyperallergic.com/feed/", "art", 1, True),
    ("Live Design", "https://www.livedesignonline.com/rss.xml", "stage", 1, True),
    ("IndieWire (craft)", "https://www.indiewire.com/c/craft/feed/", "film", 1, True),
    ("CineD", "https://www.cined.com/feed/", "film", 1, True),
    ("Game Developer", "https://www.gamedeveloper.com/rss.xml", "games", 1, True),
    ("Transom", "https://transom.org/feed/", "radio", 2, False),
    ("ScienceDaily (acoustics)", "https://www.sciencedaily.com/rss/matter_energy/acoustics.xml", "nature", 3, False),
    ("ScienceDaily (animals)", "https://www.sciencedaily.com/rss/plants_animals/animals.xml", "nature", 1, True),
    ("Hackaday", "https://hackaday.com/feed/", "tools", 1, True),
]

# First matching rule wins; titles are checked before summaries.
RULES = [
    ("calls", r"\b(open call|call for (works|entries|artists|proposals|submissions)|residenc|grant|commission|competition|deadline|award nominations)"),
    ("access", r"\b(accessib|deaf|hard of hearing|hearing (loss|aid)|blind|caption|tinnitus)"),
    ("games", r"\b(game audio|video ?game|Wwise|FMOD|MetaSounds|Unreal|Unity|indie game)"),
    ("field", r"\b(field record|hydrophone|contact mic|location sound|ambisonic|binaural|soundwalk|acoustic ecology)"),
    ("nature", r"\b(birds?|birdsong|whales?|bats?|insects?|frogs?|bioacoust|species|wildlife|forest|ocean|reef|animals?)\b"),
    ("radio", r"\b(podcast|radio|audio drama|audiobook|voice actor|voice-over|voiceover)"),
    ("film", r"\b(film|movie|series|cinema|Foley|re-recording|dubbing|soundtrack|score)\b"),
    ("stage", r"\b(theatre|theater|dance|opera|choreograph|stage|musical)\b"),
    ("space", r"\b(architect|concert hall|auditorium|pavilion|room acoustics|acoustic panel|building)"),
    ("visual", r"\b(TouchDesigner|visuals|VJ|projection|creative coding|Processing|p5\.js|shader|audiovisual|AV show)"),
    ("art", r"\b(installation|exhibition|sound art|gallery|museum|biennale|sculpture)"),
    ("design", r"\b(sonic branding|sound logo|UX|product sound|notification sound|EV sound)"),
    ("synthesis", r"\b(synth|synthesi[sz]er|Eurorack|modular|oscillator|drum machine|sampler|sequencer|groovebox)"),
    ("sounddesign", r"\b(sound design|SFX|sound effects?|sound library)"),
    ("tools", r"\b(plug-?in|VST|AU\b|CLAP|DAW|app|software|Max/MSP|Max for Live|Pure Data|SuperCollider|VCV|open[- ]source|firmware)"),
    ("music", r"\b(album|release|composer|composition|EP|LP|track|concert|festival)\b"),
]
SOUNDY = re.compile(r"\b(sound|audio|music|acoustic|listen|noise|sonic|voice|song|hear|hearing|ears?|composer|recording|synth|soundtrack|score|silence|echo)", re.I)
SKIP = re.compile(r"\b(deal|deals|sale|% off|Black Friday|Cyber Monday|discount|giveaway|win a|best .* to buy|buyer'?s guide|sponsored)\b", re.I)
FREE = re.compile(r"\bfree\b", re.I)

# Commons categories that mark something as not a camera photograph.
NOT_PHOTO = re.compile(r"(drawing|illustration|painting|engraving|lithograph|diagram|poster|map|logo|icon|svg|"
                       r"rendering|render|computer[- ]generated|AI[- ]generated|generated|artificial intelligence|"
                       r"clip ?art|cartoon|scan of|scanned|sheet music|score|manuscript)", re.I)
LANGS = {"en": "English", "it": "Italian", "de": "German", "fr": "French", "es": "Spanish", "pt": "Portuguese",
         "la": "Latin", "ja": "Japanese", "nl": "Dutch", "sv": "Swedish", "no": "Norwegian", "fi": "Finnish"}
POEM_WORDS = ["sound", "silence", "song", "bell", "echo", "voice", "music", "wind", "hear", "listen",
              "thunder", "whisper", "rain", "sea", "bird", "night", "lute", "harp", "singing", "murmur"]

# ---------- helpers ----------

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fetch_json(url):
    return json.loads(fetch(url).decode("utf-8"))

def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()

def sentences(s, limit=650, keep=3):
    """First `keep` sentences of s, at most `limit` characters, cut at a sentence end."""
    s = (s or "").strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])", s)
    out = ""
    for p in parts[:keep]:
        if len(out) + len(p) + 1 > limit and out: break
        out = (out + " " + p).strip()
    if len(out) > limit:
        out = out[:limit].rsplit(" ", 1)[0] + "…"
    return out

def load_bank(name):
    p = BANK / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

def past_seeds(days=None):
    out = []
    for p in sorted((DATA / "seeds").glob("seed-*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if days is not None:
            try:
                age = (TODAY - datetime.date.fromisoformat(d.get("key", p.stem[5:]))).days
            except Exception:
                continue
            if age > days or age < 0: continue
        out.append(d)
    return out

def least_recent(pool, key, history):
    """Entries never used come first, then those used longest ago; ties are shuffled by date."""
    last = {}
    for day, k in history: last[k] = day
    pool = list(pool); RND.shuffle(pool)
    return sorted(pool, key=lambda x: last.get(key(x), ""))

# ---------- Wikipedia / Wiktionary / Commons / PoetryDB ----------

def wiki_summary(title, lang="en"):
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe="")
    d = fetch_json(url)
    if d.get("type") != "standard" or not d.get("extract"): return None
    return {"title": d.get("title") or title, "extract": d["extract"],
            "url": d.get("content_urls", {}).get("desktop", {}).get("page") or f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "image": (d.get("originalimage") or {}).get("source")}

def commons_photos(titles):
    """Look up File: titles on Commons; return the ones that are real camera photographs."""
    if not titles: return []
    q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "titles": "|".join(titles),
                                "iiprop": "url|extmetadata|metadata|mime|size", "iiurlwidth": "1600", "iimetadataversion": "latest"})
    d = fetch_json("https://commons.wikimedia.org/w/api.php?" + q)
    out = []
    for page in (d.get("query", {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [None])[0]
        if not info or info.get("mime") != "image/jpeg" or (info.get("width") or 0) < 800: continue
        exif = {m.get("name"): m.get("value") for m in (info.get("metadata") or []) if isinstance(m, dict)}
        if not (exif.get("Make") or exif.get("Model")): continue          # must come from a camera
        em = {k: (v or {}).get("value", "") for k, v in (info.get("extmetadata") or {}).items()}
        if NOT_PHOTO.search(em.get("Categories", "") + " " + page["title"]): continue
        artist = strip_html(em.get("Artist", ""))
        if re.search(r"\b(AI|Midjourney|DALL|Stable Diffusion)\b", artist): continue
        name = page["title"].split(":", 1)[1]
        desc = strip_html(em.get("ImageDescription", ""))
        obj = strip_html(em.get("ObjectName", "")) or re.sub(r"\.[A-Za-z]+$", "", name).replace("_", " ")
        ph = {"src": info.get("thumburl") or info["url"], "page": info.get("descriptionurl") or "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_")),
              "title": obj[:120], "alt": sentences(desc, 300, 2) or obj, "credit": artist[:120] or "via Wikimedia Commons"}
        lic = strip_html(em.get("LicenseShortName", ""))
        if lic: ph["licence"] = lic
        out.append(ph)
    return out

def photo_from_url(url):
    if not url or "upload.wikimedia.org/wikipedia/commons/" not in url: return None
    name = urllib.parse.unquote(url.rsplit("/", 1)[1])
    try:
        got = commons_photos(["File:" + name])
    except Exception as e:
        print(f"photo lookup failed: {e}", file=sys.stderr); return None
    return got[0] if got else None

def photo_from_categories(used_pages):
    cats = load_bank("photo_categories.json")
    hist = [(d.get("key", ""), (d.get("photo") or {}).get("category", "")) for d in past_seeds()]
    for cat in least_recent(cats, lambda c: c, hist)[:8]:
        try:
            q = urllib.parse.urlencode({"action": "query", "format": "json", "list": "categorymembers", "cmtitle": "Category:" + cat,
                                        "cmtype": "file", "cmlimit": "200"})
            files = [m["title"] for m in fetch_json("https://commons.wikimedia.org/w/api.php?" + q).get("query", {}).get("categorymembers", [])
                     if m["title"].lower().endswith((".jpg", ".jpeg"))]
            RND.shuffle(files)
            for i in range(0, min(len(files), 60), 20):
                for ph in commons_photos(files[i:i + 20]):
                    if ph["page"] not in used_pages:
                        ph["category"] = cat
                        return ph
        except Exception as e:
            print(f"skip category {cat}: {e}", file=sys.stderr)
    return None

def seed_concept(used):
    bank = load_bank("concepts.json")
    hist = [(d.get("key", ""), (d.get("seed") or {}).get("text", "")) for d in past_seeds() if (d.get("seed") or {}).get("kind") == "concept"]
    for c in least_recent(bank, lambda c: c["text"], hist)[:10]:
        if c["text"] in used: continue
        try:
            s = wiki_summary(c["title"])
        except Exception as e:
            print(f"skip concept {c['title']}: {e}", file=sys.stderr); continue
        if not s: continue
        paras = s["extract"].split("\n")
        note = "\n\n".join(x for x in [sentences(paras[0], 700, 4)] + ([sentences(paras[1], 500, 3)] if len(paras) > 1 else []) if x)
        seed = {"kind": "concept", "text": c["text"], "note": note, "quoted": True,
                "source": {"label": "Wikipedia: " + s["title"], "url": s["url"]}}
        return seed, s.get("image")
    return None, None

def seed_word(used):
    bank = load_bank("words.json")
    hist = [(d.get("key", ""), (d.get("seed") or {}).get("text", "")) for d in past_seeds() if (d.get("seed") or {}).get("kind") == "word"]
    for w in least_recent(bank, lambda w: w["word"], hist)[:10]:
        if w["word"] in used: continue
        try:
            d = fetch_json("https://en.wiktionary.org/api/rest_v1/page/definition/" + urllib.parse.quote(w["word"], safe=""))
        except Exception as e:
            print(f"skip word {w['word']}: {e}", file=sys.stderr); continue
        entries = d.get(w["lang"]) or []
        if not entries: continue
        e = entries[0]
        defs = [strip_html(x.get("definition", "")) for x in e.get("definitions", [])]
        defs = [x for x in defs if x][:3]
        if not defs: continue
        lang = e.get("language") or LANGS.get(w["lang"], w["lang"])
        note = f"{lang} {e.get('partOfSpeech', '').lower()}. Wiktionary gives: " + " ".join(f"({i + 1}) {x}" for i, x in enumerate(defs))
        url = "https://en.wiktionary.org/wiki/" + urllib.parse.quote(w["word"]) + "#" + urllib.parse.quote(lang.replace(" ", "_"))
        return {"kind": "word", "text": w["word"], "lang": lang, "note": note, "quoted": True,
                "source": {"label": "Wiktionary: " + w["word"], "url": url}}
    return None

def poem_pick(recent_authors, used_titles):
    words = POEM_WORDS[:]; RND.shuffle(words)
    for word in words[:6]:
        try:
            got = fetch_json("https://poetrydb.org/lines/" + urllib.parse.quote(word) + "/author,title,lines,linecount")
        except Exception as e:
            print(f"poetrydb {word}: {e}", file=sys.stderr); continue
        if not isinstance(got, list): continue
        ok = [p for p in got if 4 <= int(p.get("linecount") or 0) <= 36
              and p.get("author") not in recent_authors and p.get("title") not in used_titles]
        if not ok: continue
        p = RND.choice(ok)
        lines = [l.rstrip() for l in p["lines"]]
        text = "\n".join(lines)
        text = re.sub(r"\n{2,}", "\n\n", text).strip()
        return {"title": p["title"], "author": p["author"], "lang": "English", "text": text,
                "note": "Public-domain text from PoetryDB, which draws its poems from Project Gutenberg. Chosen automatically.",
                "source": {"label": "PoetryDB", "url": "https://poetrydb.org/title/" + urllib.parse.quote(p["title"]) + "/author,title,lines"}}
    return None

def listen_pick(used_urls):
    bank = load_bank("listen.json")
    hist = [(d.get("key", ""), (d.get("listen") or {}).get("work", "")) for d in past_seeds()]
    for L in least_recent(bank, lambda x: x["work"], hist)[:8]:
        try: s = wiki_summary(L["title"])
        except Exception as e:
            print(f"skip listen {L['title']}: {e}", file=sys.stderr); continue
        if not s or s["url"] in used_urls: continue
        out = {"artist": L["artist"], "work": L["work"], "why": sentences(s["extract"], 600, 3), "url": s["url"], "quoted": True}
        if L.get("year"): out["year"] = L["year"]
        return out
    return None

def crossover_pick(last_field, used_urls):
    bank = [c for c in load_bank("crossover.json") if c["field"] != last_field]
    hist = [(d.get("key", ""), (d.get("crossover") or {}).get("title", "")) for d in past_seeds()]
    for C in least_recent(bank, lambda x: x["title"], hist)[:8]:
        try: s = wiki_summary(C["wiki"])
        except Exception as e:
            print(f"skip crossover {C['wiki']}: {e}", file=sys.stderr); continue
        if not s or s["url"] in used_urls: continue
        return {"field": C["field"], "title": C["title"], "body": sentences(s["extract"], 700, 4),
                "source": "Wikipedia", "url": s["url"], "quoted": True}
    return None

# ---------- news ----------

def text_of(el, *names):
    for n in names:
        x = el.find(n)
        if x is not None and (x.text or "").strip(): return x.text.strip()
        if x is not None and x.get("href"): return x.get("href")
    return ""

def clean(s):
    s = strip_html(s)
    s = re.sub(r"\s*(The post .* appeared first on .*|Read more.*|Continue reading.*)$", "", s)
    if len(s) > 300:
        cut = s[:300]
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        s = cut[: end + 1] if end > 120 else cut.rsplit(" ", 1)[0] + "…"
    return s

def parse_date(s):
    if not s: return None
    try: d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try: d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception: return None
    if d.tzinfo is None: d = d.replace(tzinfo=datetime.timezone.utc)
    return d.astimezone(TZ)

def feed_items(xml):
    root = ET.fromstring(xml)
    for el in root.iter():
        if el.tag.endswith("}entry"): el.tag = "entry"
        elif "}" in el.tag: el.tag = el.tag.split("}", 1)[1]
    for it in list(root.iter("item")) + list(root.iter("entry")):
        yield {"title": clean(text_of(it, "title")), "url": text_of(it, "link", "guid").strip(),
               "date": parse_date(text_of(it, "pubDate", "published", "updated", "date")),
               "summary": clean(text_of(it, "description", "summary", "encoded", "content"))}

def categorise(title, summary, default):
    for blob in (title, title + " " + summary):
        for cat, rx in RULES:
            if re.search(rx, blob, re.I): return cat
    return default

def build_items(seen):
    hours = 72 if TODAY.weekday() == 0 else 48
    since = NOW - datetime.timedelta(hours=hours)
    found, used_sources = [], []
    for name, url, default, prio, filt in FEEDS:
        try: got = list(feed_items(fetch(url)))
        except Exception as e:
            print(f"skip feed {name}: {e}", file=sys.stderr); continue
        n = 0
        for it in got:
            if not it["title"] or not it["url"].startswith("http") or it["url"] in seen: continue
            if not it["date"] or it["date"] < since or it["date"] > NOW + datetime.timedelta(hours=2): continue
            if SKIP.search(it["title"]): continue
            if filt and not SOUNDY.search(it["title"] + " " + it["summary"]): continue
            seen.add(it["url"])
            e = {"cat": categorise(it["title"], it["summary"], default), "signal": 1, "auto": True,
                 "date": it["date"].date().isoformat(), "title": it["title"], "take": it["summary"], "source": name, "url": it["url"]}
            if FREE.search(it["title"]): e["free"] = True
            found.append((prio, it["date"], n, e)); n += 1
        if n: used_sources.append(name)
    found = [f for f in found if f[2] < 3]                       # up to 3 per source
    found.sort(key=lambda f: (f[2], -f[0], -f[1].timestamp()))   # round-robin by priority, newest first
    items = [f[3] for f in found[:24]]
    for it in items[:6]: it["signal"] = 2
    start = since.date()
    rng = f"{start.day} {start.strftime('%B')} – {TODAY.day} {TODAY.strftime('%B %Y')}"
    return items, used_sources, hours, rng

# ---------- main ----------

def main():
    (DATA / "seeds").mkdir(parents=True, exist_ok=True)
    out = DATA / "seeds" / f"seed-{KEY}.json"
    if out.exists():
        print(f"{out.name} exists, leaving it"); return

    recent = past_seeds(30)
    used_seed = {(d.get("seed") or {}).get("text") for d in recent}
    used_pages = {(d.get("photo") or {}).get("page") for d in past_seeds()}
    used_urls = {(d.get(k) or {}).get("url") for d in recent for k in ("listen", "crossover")}
    recent_authors = {(d.get("poem") or {}).get("author") for d in recent}
    used_titles = {(d.get("poem") or {}).get("title") for d in past_seeds()}
    seen = {i.get("url") for d in past_seeds(10) for i in d.get("items", [])}
    last = sorted(past_seeds(), key=lambda d: d.get("key", ""))
    last_field = (last[-1].get("crossover") or {}).get("field") if last else None

    # Seed kind rotates by day: concept, word, photo.
    order = ["concept", "word", "photo"]
    start = order[TODAY.toordinal() % 3]
    order = order[order.index(start):] + order[:order.index(start)]
    seed, photo = None, None
    for kind in order:
        if kind == "concept":
            seed, img = seed_concept(used_seed)
            if seed:
                ph = photo_from_url(img)
                if ph and ph["page"] not in used_pages: photo = ph
        elif kind == "word":
            seed = seed_word(used_seed)
        elif kind == "photo":
            photo = photo_from_categories(used_pages)
            if photo:
                seed = {"kind": "photo", "text": photo["title"], "note": photo["alt"], "photo": photo, "quoted": True,
                        "source": {"label": "Wikimedia Commons", "url": photo["page"]}}
        if seed: break
    if not seed:
        sys.exit("could not build a seed today (all lookups failed); not writing a file")
    if not photo:
        photo = photo_from_categories(used_pages)

    poem = poem_pick(recent_authors, used_titles)
    listen = listen_pick(used_urls)
    cross = crossover_pick(last_field, used_urls)
    items, used_sources, hours, rng = build_items(seen)

    srcs = ", ".join(used_sources[:5]) + (f" and {len(used_sources) - 5} more" if len(used_sources) > 5 else "")
    doc = {"key": KEY, "label": LABEL, "range": rng, "generated": NOW.isoformat(timespec="seconds"), "auto": True, "seed": seed}
    if photo: doc["photo"] = photo
    if poem: doc["poem"] = poem
    if listen: doc["listen"] = listen
    if cross: doc["crossover"] = cross
    if items:
        doc["headline"] = "New across the crafts"
        doc["lead"] = (f"{len(items)} new stories from {len(used_sources)} source{'s' if len(used_sources) != 1 else ''} over the last {hours} hours, including {srcs}. "
                       "This edition is assembled automatically from the outlets' own feeds: titles and summaries are theirs. Open a story for the full article.")
        doc["items"] = items
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out.name}: {seed['kind']} '{seed['text']}', photo={'yes' if photo else 'no'}, poem={'yes' if poem else 'no'}, {len(items)} items")

if __name__ == "__main__":
    main()
