# Fabric App Learnings

Field notes from building more than twenty **Fabric Apps** — 3D digital twins, data stories and
internal tools on Microsoft Fabric.

**📖 Read them as a site: <https://kornalexander.github.io/Fabric-App-Learnings/>**

These are working notes I wrote to myself while building, not documentation written afterwards. The
🔴 markers are the expensive ones — nearly every line exists because I got something wrong first.

---

## The playbooks

| | What it covers |
|---|---|
| [**The drone camera**](playbooks/drone-camera.md) | One `flyControls.ts`, byte-identical across eight Three.js apps and ported to Cesium. Why it has no toggle button; the `OrbitControls` hand-back bug that was in every app with free flight from day one; the four Cesium traps |
| [**Realistic 3D terrain**](playbooks/realistic-3d-terrain.md) | What actually buys realism, in order of effect. Proving registration with facts that fall *out* of the data. Mesh quantisation, 390k instanced trees, land-cover rasters that get *smaller* as they get finer. And the bug class that survives the entire verification chain |
| [**The three limitations**](playbooks/fabric-app-limits.md) | Server-side functions, the public URL, and capacity sizing — measured rather than felt, each with the route that works today |
| [**Photoreal 3D maps**](playbooks/photoreal-3d-maps.md) | Renderer vs broker vs content, and why conflating them is where cost surprises come from. Includes the token-free route |
| [**Choosing a front end**](playbooks/choosing-a-front-end.md) | Report, app or low-code — a decision guide rather than a scorecard |

## The calculator

An **unofficial, untested** estimator for what a Fabric App consumes in capacity units and which SKU
it fits into:
<https://kornalexander.github.io/Fabric-App-Learnings/calculator/>

> ⚠️ **Not an official Microsoft tool. Not tested. Not supported.** The CU coefficients are my own
> rough estimates, not published figures — they are editable in the tool, and you should replace them
> with numbers from the Fabric Capacity Metrics app. **Do not use it to quote a customer, size a
> purchase, or make a budget decision.**

It is a single self-contained HTML file with no dependencies and no network calls. Download
[`docs/calculator/tool.html`](docs/calculator/tool.html) and it works offline.

## Where the code lives

The playbooks describe patterns; the runnable templates are in
[microsoft/awesome-rayfin](https://github.com/microsoft/awesome-rayfin):

- [`templates/pbi-fixer`](https://github.com/microsoft/awesome-rayfin/tree/main/templates/pbi-fixer) — reads a real semantic model, finds issues, writes fixes back
- [`templates/ibcs-trainer`](https://github.com/microsoft/awesome-rayfin/tree/main/templates/ibcs-trainer) — three games on one shared IBCS rule registry
- [Paragliding Insights (PR #92)](https://github.com/microsoft/awesome-rayfin/pull/92) — 3D flying map with IGC replay, and the home of `flyControls.ts`

---

## Repo layout

```
playbooks/          the markdown sources — edit these
docs/               the published site (GitHub Pages serves this folder)
  index.html          landing page
  *.html              one page per playbook, generated
  calculator/         the calculator + its disclaimer wrapper
  assets/css/         one stylesheet, hand-written
tools/build.py      renders playbooks/*.md -> docs/*.html
```

## Building

No static-site generator, no `node_modules`, no pipeline. One Python script and one stylesheet:

```bash
pip install markdown
python tools/build.py
```

Then open `docs/index.html`. The site is plain static files — GitHub Pages serves `docs/` directly.

---

## Disclaimer

**Not affiliated with, endorsed by, or representing Microsoft.** These are personal notes about
publicly available technology, written in my own time. Nothing here is official guidance, none of it
is tested beyond my own use, and product behaviour and pricing both drift — verify before you rely on
anything.

Licensed [MIT](LICENSE). Corrections welcome via issues or pull requests.
