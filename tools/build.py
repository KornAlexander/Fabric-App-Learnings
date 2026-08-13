"""Render playbook markdown -> styled HTML pages for the Fabric-App-Learnings site.

Hand-rolled on purpose: no static-site generator, no build pipeline, no node_modules.
Run:  python tools/build.py
"""
from __future__ import annotations

import html
import pathlib
import re

import markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "playbooks"
OUT = ROOT / "docs"
REPO = "https://github.com/KornAlexander/Fabric-App-Learnings"

# slug -> (nav label, page title, one-line subtitle, source markdown)
PAGES = {
    "drone-camera": (
        "Drone camera",
        "The drone camera",
        "One file, eight apps, two renderers — the latch design, the hand-back bug, and the Cesium traps.",
        "drone-camera.md",
    ),
    "3d-terrain": (
        "3D terrain",
        "Realistic 3D terrain in the browser",
        "What actually buys realism, how to prove the map is in the right place, and the bugs only a rendered pixel reveals.",
        "realistic-3d-terrain.md",
    ),
    "limitations": (
        "What to plan for",
        "Fabric Apps — three things to plan for",
        "Rayfin functions, the public URL, and capacity sizing. Measured, not assumed — each with the route that works today.",
        "fabric-app-limits.md",
    ),
    "photoreal-maps": (
        "Photoreal maps",
        "Photoreal 3D maps — what you actually pay for",
        "Renderer, broker and content are three different things. Most cost surprises come from conflating them.",
        "photoreal-3d-maps.md",
    ),
    "choosing": (
        "Choosing a front end",
        "Choosing a front end",
        "Report, app or low-code — a decision guide, not a scorecard.",
        "choosing-a-front-end.md",
    ),
}

NAV = [("index.html", "Home")] + [
    (f"{slug}.html", meta[0]) for slug, meta in PAGES.items()
] + [("calculator/index.html", "Calculator")]


def nav_html(current: str, depth: int = 0) -> str:
    up = "../" * depth
    items = []
    for href, label in NAV:
        cls = ' class="active"' if href == current else ""
        items.append(f'<a href="{up}{href}"{cls}>{html.escape(label)}</a>')
    return "\n        ".join(items)


def shell(*, title: str, subtitle: str, body: str, current: str, depth: int = 0,
          hero_extra: str = "", head_extra: str = "") -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)} · Fabric App Learnings</title>
<meta name="description" content="{html.escape(subtitle)}" />
<link rel="stylesheet" href="{up}assets/css/style.css" />
{head_extra}</head>
<body>

<nav class="top">
  <div class="wrap">
    <a class="logo" href="{up}index.html">Fabric App <span>Learnings</span></a>
    <div class="links">
        {nav_html(current, depth)}
    </div>
  </div>
</nav>

<header class="hero compact">
  <div class="wrap">
    <h1>{html.escape(title)}</h1>
    <p class="sub">{html.escape(subtitle)}</p>
    {hero_extra}
  </div>
</header>

{body}

<footer class="site">
  <div class="wrap">
    <p><strong>Personal field notes.</strong> Written for myself while building things, shared in case
       they save someone else the same days.</p>
    <p>Not affiliated with, endorsed by, or representing Microsoft. Nothing here is official guidance,
       and nothing here is tested beyond my own use.</p>
    <p>Markdown sources and issues: <a href="{REPO}">{REPO}</a> · MIT licence.</p>
  </div>
</footer>

</body>
</html>
"""


def build_article(slug: str) -> None:
    label, title, subtitle, filename = PAGES[slug]
    text = (SRC / filename).read_text(encoding="utf-8")

    # drop the H1 and the leading blockquote — the hero already says both
    text = re.sub(r"^#\s+.*$", "", text, count=1, flags=re.M)

    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"])
    rendered = md.convert(text)

    toc_items = re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>', rendered, flags=re.S)
    toc = ""
    if len(toc_items) > 2:
        links = "\n".join(
            f'      <li><a href="#{anchor}">{re.sub("<[^>]+>", "", head).strip()}</a></li>'
            for anchor, head in toc_items
        )
        toc = f'<div class="toc"><strong>On this page</strong>\n    <ul>\n{links}\n    </ul>\n  </div>'

    # tables get their own scroll container on narrow screens
    rendered = rendered.replace("<table>", '<div class="table-scroll"><table>').replace(
        "</table>", "</table></div>"
    )

    body = f"""<section>
  <div class="wrap reading">
    {toc}
    <article>
{rendered}
    </article>
    <p style="margin-top:3rem"><a class="btn btn-outline"
       href="{REPO}/blob/main/playbooks/{filename}">Read the markdown source on GitHub</a></p>
  </div>
</section>"""

    (OUT / f"{slug}.html").write_text(
        shell(title=title, subtitle=subtitle, body=body, current=f"{slug}.html"),
        encoding="utf-8",
    )
    print(f"  {slug}.html  <- playbooks/{filename}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("building pages:")
    for slug in PAGES:
        build_article(slug)
    print("done.")


if __name__ == "__main__":
    main()
