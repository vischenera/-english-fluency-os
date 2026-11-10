#!/usr/bin/env python3
"""Build the printable A4 workbook from the Markdown sources.

    pip install -r print/requirements.txt
    python print/build_pdf.py              # writes print/English.pdf
    python print/build_pdf.py --html x.html  # also keeps the intermediate HTML

The workbook is laid out as modules (chapters), not cards: each module starts
on a new page, deck entries are numbered items that never split across pages,
file references become page references, and the trackers get writing space.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt
from weasyprint import HTML

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# The printed book is personal: it carries a plain title and no "who it is for" description.
TITLE = "English"
DEFAULT_OUT = HERE / "English.pdf"


@dataclass
class Module:
    title: str
    source: str
    slug: str
    number: int = 0
    part: str = ""


PARTS = [
    ("Part I", "The System", [
        Module("Start Here", "README.md", "start-here"),
        Module("Daily 10-Minute Protocol", "daily/10_minute_protocol.md", "daily-protocol"),
        Module("Roadmap", "roadmap.md", "roadmap"),
        Module("Weekly Sprints", "weekly/weekly_sprints.md", "weekly-sprints"),
        Module("Review Protocol", "reviews/review_protocol.md", "review-protocol"),
        Module("Metrics", "metrics.md", "metrics"),
    ]),
    ("Part II", "Speaking Toolkit", [
        Module("Frameworks", "curriculum/frameworks/framework_cards.md", "frameworks"),
        Module("Chunks & Collocations", "curriculum/vocabulary/strategic_vocabulary.md", "chunks"),
        Module("Expressions", "curriculum/expressions/expression_library.md", "expressions"),
        Module("Corrections", "curriculum/corrections/common_corrections.md", "corrections"),
        Module("Conversation Islands", "curriculum/islands/conversation_islands.md", "islands"),
        Module("Prompt Bank", "daily/prompt_bank.md", "prompt-bank"),
    ]),
    ("Part III", "Accent: General American", [
        Module("Accent Overview", "curriculum/accent/00_overview.md", "accent-overview"),
        Module("Prosody", "curriculum/accent/01_prosody.md", "prosody"),
        Module("Segmental Tells", "curriculum/accent/02_segmental_tells.md", "segmental-tells"),
        Module("Connected Speech", "curriculum/accent/03_connected_speech.md", "connected-speech"),
        Module("Core Word List", "curriculum/accent/04_core_word_list.md", "core-word-list"),
        Module("Micro-Imitation Protocol", "curriculum/accent/micro_imitation_protocol.md", "micro-imitation"),
    ]),
    ("Part IV", "Trackers", [
        Module("Progress Tracker", "tracking/progress_tracker.md", "progress-tracker"),
    ]),
]

# How each deck's fields are laid out. Fields not named here print as "Label  value" lines.
DECKS = {
    "F": {"gloss": "Use", "examples": "Examples"},
    "V": {"gloss": "Means", "examples": "Example"},
    "E": {"gloss": "Use", "meta": "Tag"},
    "C": {"gloss": "Why", "examples": "Examples", "correction": True},
    "PR": {},
    "SG": {},
    "CS": {"gloss": "What it is"},
}

ENTRY_RE = re.compile(r"^#{2,3} (?P<id>(?P<deck>F|V|E|C|PR|SG|CS)\d+)\. (?P<title>.+)$")
FIELD_RE = re.compile(r"^- \*\*(?P<label>[^*]+?):\*\* ?(?P<value>.*)$")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF]️? ?")

md = MarkdownIt("commonmark", {"typographer": False}).enable(["table", "strikethrough"])


@dataclass
class Entry:
    id: str
    deck: str
    title: str
    fields: list[tuple[str, str]] = field(default_factory=list)


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    return md.renderInline(text)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def strip_h1(text: str) -> str:
    return re.sub(r"\A# .*\n+", "", text)


def drop_section(text: str, heading: str) -> str:
    """Remove a '## heading' section up to the next '## ' heading."""
    return re.sub(rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## )", "", text)


def split_segments(text: str):
    """Yield ('md', markdown) and ('entry', Entry) segments in source order."""
    lines, buf, i = text.split("\n"), [], 0
    while i < len(lines):
        m = ENTRY_RE.match(lines[i])
        if not m:
            buf.append(lines[i])
            i += 1
            continue
        if buf:
            yield "md", "\n".join(buf)
            buf = []
        entry = Entry(m["id"], m["deck"], m["title"])
        i += 1
        while i < len(lines) and (f := FIELD_RE.match(lines[i])):
            entry.fields.append((f["label"], f["value"]))
            i += 1
        yield "entry", entry
    if buf:
        yield "md", "\n".join(buf)


@dataclass
class Shared:
    """A field repeated across a whole deck, printed once above its entries."""
    note: str
    short: dict[str, str] = field(default_factory=dict)  # per-entry remainder; empty = drop the field


def shared_fields(entries: list[Entry]) -> dict[str, Shared]:
    """Find fields every entry repeats.

    Identical values are dropped from the entries. Values that differ only in a
    short middle (like the word to search for) keep just that middle per entry.
    """
    if len(entries) < 2:
        return {}
    shared = {}
    for label, _ in entries[0].fields:
        values = [dict(e.fields).get(label) for e in entries]
        if None in values:
            continue
        if len(set(values)) == 1:
            shared[label] = Shared(values[0])
            continue
        prefix = os.path.commonprefix(values)
        suffix = os.path.commonprefix([v[::-1] for v in values])[::-1]
        prefix = prefix[:max(prefix.rfind(" "), prefix.rfind('"')) + 1]  # cut back to a word edge
        cuts = [i for i in (suffix.find(" "), suffix.find('"')) if i >= 0]
        suffix = suffix[min(cuts):] if cuts else ""
        middles = [v[len(prefix):len(v) - len(suffix)] for v in values]
        if len(prefix) + len(suffix) < 40 or not all(0 < len(m) <= 20 for m in middles):
            continue
        quote_l, quote_r = prefix[-1:] == '"', suffix[:1] == '"'
        prefix, suffix = prefix[:len(prefix) - quote_l], suffix[quote_r:]
        wrap = ('"' if quote_l else "", '"' if quote_r else "")
        shared[label] = Shared(f"{prefix}{wrap[0]}…{wrap[1]}{suffix}",
                               {e.id: f"{wrap[0]}{m}{wrap[1]}" for e, m in zip(entries, middles)})
    return shared


def label_text(label: str) -> str:
    return EMOJI_RE.sub("", label).strip()


def render_entry(e: Entry, shared: dict[str, Shared]) -> str:
    style = DECKS[e.deck]
    if style.get("correction") and " → " in e.title:
        wrong, right = e.title.split(" → ", 1)
        title = (f'<span class="wrong">{inline(wrong)}</span> <span class="arrow">→</span> '
                 f'<span class="right">{inline(right)}</span>')
    else:
        title = inline(e.title)
    meta, body = "", []
    for label, value in e.fields:
        if label in shared:
            if not shared[label].short:
                continue
            value = shared[label].short[e.id]
        if label == style.get("meta"):
            tag = value.split(" · ")[0].strip()
            formality = re.search(r"\*\*Formality:\*\*\s*(.+)$", value)
            meta = f'<span class="meta">{esc(tag)}{" · " + esc(formality[1]) if formality else ""}</span>'
        elif label == style.get("gloss"):
            body.append(f'<p class="gloss">{inline(value)}</p>')
        elif label == style.get("examples"):
            items = "".join(f"<li>{inline(x.strip())}</li>" for x in value.split(" / "))
            body.append(f'<ul class="examples">{items}</ul>')
        else:
            body.append(f'<p class="field field-{slugify(label_text(label))}">'
                        f'<span class="label">{esc(label_text(label))}</span> {inline(value)}</p>')
    return (f'<div class="entry" id="{e.id}"><span class="entry-id">{e.id}</span>'
            f'<p class="entry-title">{title}{meta}</p>{"".join(body)}</div>')


def render_shared(shared: dict[str, Shared], intro: str = "") -> str:
    """Print each shared field once, unless the module intro already says it."""
    def norm(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return "".join(
        f'<p class="hoisted"><span class="label">{esc(label_text(k))} for every entry:</span> {inline(s.note)}</p>'
        for k, s in shared.items() if norm(s.note)[:40] not in norm(intro))


def render_module_body(module: Module) -> tuple[str, list[str]]:
    """Return the module's HTML and the IDs of its entries."""
    text = strip_h1((ROOT / module.source).read_text(encoding="utf-8"))
    if module.source == "README.md":
        text = text.split("\n\n", 1)[1]  # skip the "who it is for" line, like the cover
        text = drop_section(text, "Repository Map")  # the contents page replaces it
    segments = list(split_segments(text))
    entries = [s for kind, s in segments if kind == "entry"]
    shared = shared_fields(entries)
    out, intro_done = [], not shared
    for kind, seg in segments:
        if kind == "entry":
            if not intro_done:
                out.append(render_shared(shared))
                intro_done = True
            out.append(render_entry(seg, shared))
            continue
        if not intro_done:
            # Put the "for every entry" note at the end of the intro, before the first group heading.
            head, sep, rest = seg.partition("\n## ")
            out.append(md.render(head))
            out.append(render_shared(shared, head))
            intro_done = True
            seg = ("## " + rest) if sep else ""
        out.append(md.render(seg))
    return "".join(out), [e.id for e in entries]


def link_targets(modules: list[Module]) -> dict[str, Module]:
    targets = {}
    for m in modules:
        targets[m.source] = m
        targets[Path(m.source).name] = m
    targets["curriculum/accent/"] = next(m for m in modules if m.slug == "accent-overview")
    return targets


def add_page_references(body: str, targets: dict[str, Module]) -> str:
    """Turn `path/to/file.md` mentions into printed page references."""
    def target(path: str) -> Module | None:
        return targets.get(html.unescape(path))

    def paren(m: re.Match) -> str:  # "(`01_prosody.md`)" -> "(p. 12)"
        t = target(m[1])
        return f'(<a class="xref-page" href="#mod-{t.slug}"></a>)' if t else m[0]

    def see(m: re.Match) -> str:  # "(see `x.md`)" -> "(see Title, p. 12)"
        t = target(m[1])
        return f'(see <a class="xref-see" href="#mod-{t.slug}">{esc(t.title)}</a>)' if t else m[0]

    def bare(m: re.Match) -> str:  # "`x.md`" -> "Title (p. 12)"
        t = target(m[1])
        return f'<a class="xref" href="#mod-{t.slug}">{esc(t.title)}</a>' if t else f'<code>{m[1]}</code>'

    body = re.sub(r"\(<code>([^<]+)</code>\)", paren, body)
    body = re.sub(r"\(see <code>([^<]+)</code>\)", see, body)
    return re.sub(r"<code>([^<]+)</code>", bare, body)


def decorate_forms(module: Module, body: str) -> str:
    """Give tracker tables and summary lists room to write in."""
    body = body.replace("<li>[ ] ", '<li class="task"><span class="box">☐</span> ')
    if module.slug == "progress-tracker":
        body = body.replace("<table>", '<table class="form form-week">', 1)
        body = re.sub(r"(<h2>Weekly Summary</h2>\s*)<ul>", r'\1<ul class="lines">', body)
    if module.slug == "islands":
        body = body.replace("<table>", '<table class="form form-islands">', 1)
    return body


def edition_date() -> str:
    try:
        stamp = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%cs"],
                               capture_output=True, text=True, check=True).stdout.strip()
        day = dt.date.fromisoformat(stamp)
    except (OSError, subprocess.CalledProcessError, ValueError):
        day = dt.date.today()
    return day.strftime("%B %Y")


def build_html() -> str:
    modules: list[Module] = []
    number = 0
    for part_no, part_name, part_modules in PARTS:
        for m in part_modules:
            number += 1
            m.number, m.part = number, f"{part_no} · {part_name}"
            modules.append(m)
    targets = link_targets(modules)

    toc, sections = [], []
    for part_no, part_name, part_modules in PARTS:
        toc.append(f'<p class="toc-part">{esc(part_no)} · {esc(part_name)}</p><ol class="toc-list">')
        for i, m in enumerate(part_modules):
            body, ids = render_module_body(m)
            id_range = f'<span class="toc-range">{ids[0]}–{ids[-1]}</span>' if ids else ""
            toc.append(f'<li><a href="#mod-{m.slug}"><span class="toc-num">{m.number}</span>'
                       f'{esc(m.title)}{id_range}</a></li>')
            running = f"Module {m.number} · {m.title}"
            part_attr = f' data-part="{esc(part_no)} · {esc(part_name)}"' if i == 0 else ""
            body = decorate_forms(m, add_page_references(body, targets))
            body = EMOJI_RE.sub("", body)
            sections.append(
                f'<section class="module module-{m.slug}" id="mod-{m.slug}">'
                f'<p class="eyebrow{" part-start" if i == 0 else ""}"{part_attr}>'
                f'{esc(part_no)} · {esc(part_name)} &nbsp;/&nbsp; Module {m.number}</p>'
                f'<h1 class="module-title" data-running="{esc(running)}">{esc(m.title)}</h1>'
                f'{body}</section>')
        toc.append("</ol>")

    css = (HERE / "style.css").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{TITLE}</title>
<style>{css}</style></head>
<body>
<section class="cover">
  <h1 class="cover-title">{TITLE}</h1>
  <p class="cover-date">{esc(edition_date())}</p>
</section>
<section class="toc">
  <h1 class="toc-title" data-running="Contents">Contents</h1>
  {"".join(toc)}
</section>
{"".join(sections)}
</body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT, help="PDF to write")
    parser.add_argument("--html", type=Path, help="also write the intermediate HTML here")
    args = parser.parse_args()
    document = build_html()
    if args.html:
        args.html.write_text(document, encoding="utf-8")
    HTML(string=document, base_url=str(HERE)).write_pdf(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
