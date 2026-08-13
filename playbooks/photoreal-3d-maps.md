# Photorealistic 3D Maps — Cesium ion vs. OpenStreetMap

Analysis of how **Harbour Pulse** (`fabric-harbour-pulse`) renders its photoreal Sydney Harbour,
what is reusable for our other 3D solutions, and what the licensing actually permits.

Researched 2026-08-10 against CesiumJS 1.143, Cesium ion pricing, and the Google Maps Platform price list.

---

## TL;DR — the six things that matter

1. **The photorealism is Google's, not Cesium's.** Cesium is the renderer and the broker.
   The textured 3D mesh comes from **Google Photorealistic 3D Tiles**.
2. **CesiumJS is Apache-2.0** — free, commercial use explicitly permitted, no token needed.
   Only **Cesium ion** (the hosted content/CDN service) is licensed.
3. **The Cesium ion free "Community" tier is non-commercial.** It is *not* valid for a
   company with >$50K revenue, for government projects, or for funded educational research —
   with one carve-out that is usually the relevant one: *"exploratory commercial or government
   development, e.g. evaluating if Cesium ion will meet your needs."* Internal demos sit inside
   that carve-out. Anything you hand to another organisation to run does not.
4. **Yes, you can get the identical photoreal result without a Cesium token** — set
   `Cesium.GoogleMaps.defaultApiKey` and go straight to Google. But you swap a $149/month
   flat fee for **metered per-tile billing at $6.00 / 1,000 tiles with only 1,000 free per month**,
   which is the more dangerous of the two options for a demo that gets left running.
5. **OpenStreetMap is not the "free commercial" answer people assume.** The *data* is fine
   (ODbL). The *public tile server* (`tile.openstreetmap.org`) and the *public Overpass API*
   are donated infrastructure with usage policies that rule out production and heavy use.
   And visually it is not close — grey extruded boxes, not a photoreal city. **OSM also has no
   aerial imagery whatsoever** — it is a vector database, so it cannot replace a satellite or
   orthophoto layer.
6. **There is a genuinely free, licence-clean, good-looking option, and we already ship it:**
   German state **LoD2 + DOP20 (20 cm) + DGM1**, baked to static files, rendered in Three.js with
   no map service at runtime. That is what **Campus-Scheduler** does across eight AOIs — see §5a.

---

## 1. How Harbour Pulse actually does it

All of it lives in one file, `src/components/CesiumView.tsx`.
The design is a clean **one-flag fork**: a single env var decides between two entirely different
visual stacks.

```ts
const ION_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN;
```

### Path A — token present (photoreal)

```ts
if (ION_TOKEN) Ion.defaultAccessToken = ION_TOKEN;

const viewer = new Viewer(div.current!, {
  contextOptions: { webgl: { preserveDrawingBuffer: true } },
  baseLayer: undefined,                    // Google tiles supply their own colour
  terrain: Terrain.fromWorldTerrain(),     // Cesium World Terrain (ion asset)
  // ...all default widgets disabled
});

void createGooglePhotorealistic3DTileset()
  .then((ts) => viewer.scene.primitives.add(ts))
  .catch(() => {
    // second-choice: Cesium OSM Buildings (untextured but global)
    void createOsmBuildingsAsync().then((ts) => viewer.scene.primitives.add(ts));
  });
```

Three separate ion-gated assets are in play here, which is the bit most people miss:

| Asset | What it gives | Source |
|---|---|---|
| `createGooglePhotorealistic3DTileset()` | Textured photogrammetry mesh — the actual "wow" | **Google**, brokered by ion |
| `Terrain.fromWorldTerrain()` | Global elevation | Cesium ion asset |
| `createOsmBuildingsAsync()` | Global untextured building shells | Cesium ion asset (from OSM data) |

### Path B — no token (keyless fallback)

```ts
baseLayer: ImageryLayer.fromProviderAsync(
  Promise.resolve(new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })),
  {},
),
terrain: undefined,        // flat ellipsoid — no elevation at all
```

…plus the app fetches its own building footprints from the **Overpass API** and extrudes them as
coloured polygons — in `src/services/buildings.ts`:

```ts
const OVERPASS = 'https://overpass-api.de/api/interpreter';
const BBOX = [-33.874, 151.198, -33.852, 151.221];  // hard-coded central Sydney
const query = `[out:json][timeout:30];(way["building"](${s},${w},${n},${e}););out geom;`;
```

Height is `tags.height` → else `building:levels × 3.3` → else a 9 m default, and colour is a
four-stop ramp from `#d3dae0` (low-rise) to `#6d8296` (high-rise).

### What the fallback costs you visually

| | Path A (ion token) | Path B (keyless) |
|---|---|---|
| Buildings | Photogrammetry mesh, real façades, roofs, cranes, moored boats | Flat grey extruded prisms |
| Ground | Google aerial imagery draped on real terrain | OSM *road map* raster (roads and labels, not aerial) |
| Terrain | Cesium World Terrain | None — perfect ellipsoid |
| Coverage | Global (where Google has captured) | One hard-coded bounding box |
| Trees, landmarks | Present | Absent |

It is not a degraded version of the same picture. It is a different product.

### Small implementation details worth stealing

- `preserveDrawingBuffer: true` — required if you ever want `canvas.toDataURL()` or a
  Playwright screenshot of the WebGL canvas. Costs a little performance; enable it deliberately.
- Every default Cesium widget is switched off (`baseLayerPicker`, `geocoder`, `homeButton`,
  `timeline`, `animation`, `infoBox`, `selectionIndicator`, …). Cesium looks like a toy demo
  until you do this.
- `scene.globe.enableLighting = true` + `skyAtmosphere.show = true` — cheap realism.
- Right-drag rebound to tilt/orbit; wheel kept for zoom:
  ```ts
  camCtrl.tiltEventTypes = [CameraEventType.RIGHT_DRAG, CameraEventType.PINCH];
  ```
- Ferries are glTF models placed at **+23 m** ellipsoidal height, because Sydney's geoid offset
  puts sea level there. Get this wrong and your assets float or sink.
- Heading is derived from consecutive positions (`bearing()` helper) because the TfNSW feed has
  no bearing field — with a `HEADING_OFFSET_DEG = -90` correction because the model's bow is
  authored along +Z.

---

## 2. Who is actually behind Cesium?

| | |
|---|---|
| **Legal entity** | Cesium GS, Inc., Philadelphia, PA |
| **Origin** | Started 2011 inside **Analytical Graphics, Inc. (AGI)**, an aerospace software firm, to visualise objects in space. Led by **Patrick Cozzi**. Named after the element used in atomic clocks. |
| **Open sourced** | 2012 |
| **Spun out** | 2019, as an independent venture-backed company |
| **Acquired** | **September 2024 — by Bentley Systems** (Nasdaq: **BSY**), the Exton, PA infrastructure-engineering software company (MicroStation, ProjectWise, SYNCHRO, Seequent). ~$1.5 bn revenue, 5,800 staff. |
| **Today** | Cesium is a Bentley business unit, being folded into Bentley's **iTwin** digital-twin platform. Bentley engineers now commit to the CesiumJS repo directly. |
| **Standards** | Cesium authored **3D Tiles**, now an **OGC Community Standard**. Also co-authored glTF with Khronos. |

**Why this matters to us commercially:** Cesium is no longer a neutral startup — it belongs to
**Bentley, a Microsoft partner but also a digital-twin platform vendor** whose iTwin platform
overlaps with what we position around Fabric Real-Time Intelligence and Azure Digital Twins.
Worth knowing before you put a Cesium logo on a slide in a digital-twin conversation.

Google relationship: Cesium partnered with Google Maps Platform in **May 2023** to render the
then-new Photorealistic 3D Tiles. Cesium resells/brokers Google's tiles through ion.

---

## 3. The licensing reality

### CesiumJS — the library

**Apache License 2.0.** Commercial use, modification, distribution and patent grant all
permitted. Conditions are only: keep the licence and copyright notice, state changes.
There is **no attribution-in-UI requirement** and **no token requirement** for the library itself.

> The "Cesium ion" logo you see in the corner of the Harbour Pulse app is not the CesiumJS
> licence talking — it is the **ion data credit**, injected because ion-hosted assets are in use.

### Cesium ion — the hosted content service

This is where money and restrictions live.

| Plan | Price | Rights |
|---|---|---|
| **Community** | Free | **Personal and non-commercial use only** |
| **Commercial** | **$149/mo** individual · **$524/mo** team | Commercial use *within your organisation* |
| **Premium** | $499/mo individual · $874/mo team | Same, larger quotas |
| **Custom / Self-Hosted** | Contact sales | Enterprise, on-prem |

Cesium's own FAQ — **you need a paid commercial licence if**:

- your company makes **more than $50K annual gross revenue**, or has raised >$50K, **or**
- you are working on a **government project**, **or**
- you are working on **funded educational research**, **or**
- you exceed the free quota.

And the free Community account **may** be used for:

- non-commercial personal projects, **or**
- **exploratory commercial or government development — e.g. evaluating whether ion meets your needs**, **or**
- unfunded educational activities.

> ⚠️ **Note the asterisk on every paid tier:** *"Contact us if you plan to integrate Cesium ion
> into solutions used outside your organization."* An app you hand to someone else, or one that
> runs in **their** tenant, is exactly that case — the standard Commercial plan does not obviously
> cover it. That is an integration/OEM conversation with Cesium sales.

**Where that leaves your current token:** using it to build and show internal demos and prototypes
is defensible under "exploratory development". Publishing those apps for other organisations to use,
or shipping the token in a bundle someone else runs, is not. And note the token **is** in the public
JavaScript bundle of every deployed app — anyone can read it and burn your quota.

### Google Photorealistic 3D Tiles — the actual imagery

Governed by the **Google Maps Platform Terms**, billed on Google Cloud:

| SKU | Category | Billable event | Free/month | Price |
|---|---|---|---|---|
| Map Tiles API: Photorealistic 3D Tiles (`C6E1-98B2-DBD0`) | **Enterprise** | **Every request that returns a 3D tile** | **1,000** | **$6.00 / 1,000** |
| Map Tiles API: 2D Map Tiles | Essentials | Request returning a 2D tile | 100,000 | $0.60 / 1,000 |

**Read the billable event twice.** It is **per tile**, not per session or per map load. A single
user flying around a city for a few minutes pulls **hundreds to thousands of tiles**. The 1,000
free tiles are roughly *one short demo*. There are also hard attribution requirements — the
Google logo and the data-attribution string must stay visible.

### OpenStreetMap — the keyless fallback

Two separate things, and people conflate them:

- **The data** — ODbL 1.0. Free, commercial use fine, requires attribution and has share-alike
  obligations on derived databases.
- **The public servers** — `tile.openstreetmap.org` is governed by the
  **OSMF Tile Usage Policy**: donated, volunteer-funded, and it explicitly rules out
  heavy/bulk/commercial use. `overpass-api.de` is the same deal for the Overpass API.

So Harbour Pulse's "keyless" path is fine for local dev and a one-off demo, and **not** a
licensing-clean production posture. It just moves the problem from a bill to an acceptable-use
policy. If you want OSM in production you self-host tiles or buy from MapTiler / Mapbox / Azure Maps.

---

## 4. Can I get the same realistic outcome without the Cesium token?

**Visually identical: yes — but only by going to Google directly.** The photorealism is Google's
asset. Cesium ion is a billing and delivery broker in front of it.

I verified the API exists in the shipped CesiumJS 1.143:

```
Cesium.d.ts:8027  An API key is only required if you are directly using any Google Maps APIs,
                  such as through {@link createGooglePhotorealistic3DTileset}.
Cesium.d.ts:8038  var defaultApiKey: undefined | string;
```

So the ion-free photoreal path is a **two-line change**:

```ts
import { GoogleMaps, createGooglePhotorealistic3DTileset } from 'cesium';

GoogleMaps.defaultApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

const ts = await createGooglePhotorealistic3DTileset();   // no ion token anywhere
viewer.scene.primitives.add(ts);
```

Same code path, same mesh, same pixels. You lose two things: **Cesium World Terrain** and
**Cesium OSM Buildings**, both of which are ion assets. (For photoreal you don't need either —
the Google mesh contains the terrain. You'd only miss them outside Google's coverage.)

Cesium 1.143 also ships **`Google2DImageryProvider`**, so Google satellite raster is reachable
the same keyless-of-ion way:

```ts
GoogleMaps.defaultApiKey = "your-api-key";
const p = Google2DImageryProvider.fromUrl({ mapType: "SATELLITE" });
```

**Without Google at all: no.** Nothing free reproduces photogrammetry-textured cities globally.
The honest ceiling of the open stack is *geometrically accurate but untextured* — which for
many of our use cases is genuinely enough (see Option D).

---

## 5. The options, compared

### Option A — Cesium ion token (what Harbour Pulse does today)

| Pros | Cons |
|---|---|
| Two lines of code, works instantly | Free tier is **non-commercial** |
| Bundles terrain + OSM Buildings + Google tiles behind one token | $149/mo minimum to be commercially clean |
| **Predictable flat cost** — no per-tile surprise | Token is public in the JS bundle; quota can be burned by anyone |
| Cesium absorbs the Google relationship and billing | Third-party dependency now owned by **Bentley** |
| Automatic attribution handling | "Outside your organization" use needs a separate deal |

### Option B — Direct Google Maps Platform key

| Pros | Cons |
|---|---|
| **Pixel-identical photorealism**, no Cesium ion at all | **$6.00 / 1,000 tiles**, only 1,000 free — metered, uncapped, per tile |
| No non-commercial restriction — normal GMP commercial terms | A forgotten open browser tab keeps billing |
| One less vendor between us and the data | Loses Cesium World Terrain + OSM Buildings |
| Billing lands on an existing GCP account | **Google Cloud spend at Microsoft** — political, and probably a non-starter |
| Key restrictable by HTTP referrer | Key still public in the bundle → referrer restriction is mandatory |

### Option C — Keyless OSM (the built-in fallback)

| Pros | Cons |
|---|---|
| Zero cost, zero keys, zero accounts | **Not photoreal** — grey boxes on a road map |
| Data licence (ODbL) is genuinely open | Public tile/Overpass servers **prohibit production use** |
| Great for local dev and CI | No terrain at all |
| No vendor lock-in | Overpass is slow and rate-limited; bbox is hard-coded per city |
| Honest fallback so the app never hard-fails | Share-alike obligations on derived databases |

### Option D — Self-hosted open 3D city data (LoD2 / CityGML + DOP20)

The strongest option for **German public-sector** work — and the one **Campus-Scheduler and
Campus-Insights already ship** (see §5a). **Fully free and licence-clean.** It does *not* need
Option E: German state orthophotos are better imagery than any commercial satellite layer.

| Pros | Cons |
|---|---|
| **Free and officially open** — German state surveying offices publish LoD2 + DOP20 + DGM1 nationwide | Not photogrammetry — flat-faced buildings, no cranes/awnings/trees-on-facades |
| **20 cm orthophotos** — sharper ground than Google's or Azure's satellite layers | You run the tiling pipeline and host the output |
| No usage limits, no per-tile billing, no token, no vendor account at all | Germany/EU only; no global coverage |
| Baked to static files → served from **OneLake / Azure Blob**, stays in our stack | Upfront effort per city/region (~a day per AOI once the pipeline exists) |
| Fully offline-capable → works in sovereign/air-gapped scenarios | ODbL share-alike applies to any OSM-derived database you redistribute |
| Data provenance a public-sector reviewer will accept without a procurement round | Attribution strings are mandatory, per state |

Terrain to pair with it: **Copernicus DEM GLO-30** (free) for the surrounding shell, state **DGM1**
(1 m) for the core.

### Option E — Azure Maps

The Microsoft-native answer for **global** coverage. Note it is **not free** — it is a metered
Azure service. For German AOIs, Option D beats it on quality *and* on cost.

| Pros | Cons |
|---|---|
| **On the Azure bill** — no third-party vendor, no GCP | **Not free** — metered per transaction (limited free allowance only) |
| Enterprise terms, SLA, EU data boundary | **No photorealistic 3D mesh** |
| Already covered by an existing Azure agreement | Satellite raster (Airbus) is coarser than German DOP20 |
| Global — the gap Option D cannot fill | 3D buildings must still come from elsewhere |
| Cesium ion lists Azure Maps imagery as a source (tech preview) | Tech-preview status where it's brokered via ion |

---

## 5a. The reference implementation already exists — Campus-Scheduler

**Campus-Scheduler / Campus-Insights are pure Option D, and they do not use Cesium at all.**
Verified in the repo, not assumed:

```json
"dependencies": { "three": "^0.170.0", "react": "^19.0.0", ...rayfin }
```

No `cesium`, no `azure-maps`, no `mapbox-gl`, no `maplibre`. A workspace-wide grep for
`cesium|azure.?maps|mapbox|maplibre|googleapis|tile.openstreetmap` across `src/` returns
**zero hits**. The globe is hand-built on **Three.js** with a custom terrain shader.

**Everything is baked at build time** by `tools/geodata/pipeline.py` into `public/terrain/<aoi>/`,
so the deployed app makes **no third-party map request at runtime at all** — no token, no tile
server, no quota, no attribution beacon. That is a stronger position than either Cesium option.

| Layer | Source | Licence |
|---|---|---|
| Terrain (core, 1–2 m) | State **DGM1** — LDBV / LGL / NRW / Hamburg | CC BY 4.0 · dl-de/by-2-0 |
| Terrain (shell, 30 m) | **Copernicus DEM GLO-30** | Copernicus free licence |
| Ground imagery | State **DOP20** orthophotos, **0.2 m/px** | CC BY 4.0 · dl-de/by-2-0 |
| Buildings | State **LoD2 CityGML** | CC BY 4.0 · dl-de/by-2-0 |
| Roof colour | **Measured** from the DOP20 drape (98–99.9 % coverage) | derived |
| Vegetation | Tree cadastre (Bavaria) or **nDOM** canopy detection (BW) | state licences |
| Landuse, footpaths, indoor rooms | **OpenStreetMap** via Overpass, **bulk-downloaded once** | ODbL 1.0 |

Eight campus AOIs were built this way, across four German states. Attribution is discharged in a
`NOTICE.md` in the app repo, which also flags the one genuine open item — a **campus room-data
source whose redistribution terms** block *public* release but not internal demos.

**Why the OSM usage-policy objection does not apply here:** the pipeline pulls OSM **once, at
build time**, into committed derived files. That is bulk download of ODbL data — a different
activity from pointing every visitor's browser at `tile.openstreetmap.org`. The keyless Harbour
Pulse path does the latter, which is exactly why it hit a **504** the first time it was demoed.

**How good does it actually look without any photogrammetry?** Good enough that buildings are the
subject at close range: measured per-roof colour, ALKIS-classified walls, true-scale heights, 20 cm
ground. It is not Google's mesh — no textured façades, no street furniture — but it does not read
as "the free version". It reads as a survey.

---

## 5b. Would a Cesium ion token improve the campus solution?

**Short answer: no — for the German AOIs it is a net regression, and the token on its own does
literally nothing.** Three layers to this.

### The token alone is inert

Campus-Scheduler has **no Cesium runtime**. A token is a credential for a library that is not
installed. To use one you would first add a 3D Tiles renderer — realistically
[`3d-tiles-renderer`](https://github.com/NASA-AMMOS/3DTilesRendererJS) (JPL/Caltech, **Apache-2.0**,
2.4k stars), which renders 3D Tiles in Three.js and ships examples for **both** Cesium ion tilesets
and Google Photorealistic tiles. Its own footnote: *"Requires a Google Tiles API Key **or** Cesium
Ion API Key."*

So this is an integration project, not a config flag — and note the corollary: **if you did it, you
would not need ion at all.** A Google Maps key reaches the same tiles.

### What it would genuinely gain

| Gain | Worth it? |
|---|---|
| **Textured façades** | Real. Walls are currently the app's one honest weakness — the *class* is measured, the colour is convention. |
| Street furniture, cars, captured trees | Cosmetic. |
| **Global coverage** | **The only real capability gain.** A campus in Madrid, Warsaw or Boston has no DOP20/LoD2 equivalent. |
| Cesium World Terrain | **Negative.** It is ~30 m; the campus already has **DGM1 at 1 m**. Strictly worse. |

### What it would break — this is what decides it

The campus app's value is not the scenery, it is **per-building interactivity**. Google's mesh is
one undifferentiated photogrammetry blob with **no building entities and no IDs**.

- **The explode dies.** You cannot select, isolate or explode a building that does not exist as an
  object. The signature feature of the app is gone.
- **Every lens dies.** Occupancy tint, condition grade (`aGrade` / `aRenovation`), flow — all are
  per-building *vertex attributes* on the LoD2 mesh. Google's mesh carries none of them.
- **The true-scale claim needs re-earning.** "No vertical exaggeration", validated at median
  **+0.00 m** against the survey's own `measuredHeight`. Photogrammetry has a different error
  budget, and the claim is one of the project's honesty commitments.
- **Offline / sovereign capability dies.** Air-gapped deployments become impossible.
- **The performance budget stops being closed.** Today: smallest AOI < 14 MB, largest < 34 MB
  transferred, texture 67.5 / 77.8 MB, first frame 1.2–2.0 s — all *measured ceilings*. Streaming
  tiles makes consumption open-ended and network-dependent.
- **Licensing goes backwards, and precisely for this audience.** Cesium's free tier excludes
  **government projects** and **funded educational research**. A German public university is both.
  The campus demo's audience is exactly the audience the Community tier does not cover — so it
  would mean ion Commercial *plus* the "outside your organization" conversation, replacing a stack
  that is currently CC BY 4.0 / dl-de/by-2-0 / ODbL and publishable as-is.

### The one variant that could be defensible

**Hybrid:** keep LoD2 for the campus core (where all the interactivity lives) and use photoreal
tiles only for the **surrounding context shell**, which today is deliberately coarse 30 m Copernicus.
This requires clipping the photoreal mesh where the campus sits, or you get two overlapping cities —
Cesium has `ClippingPolygon` for this natively, Three.js would need it hand-rolled.

Cost/benefit: real engineering, a reintroduced runtime key dependency, and a licence bill — to
improve scenery that was made low-detail on purpose *because it is not the subject*.

### Verdict

Not worth it for the German AOIs. Worth prototyping only if **"any campus in the world, next week"**
becomes a requirement — and even then, understand that it produces a *different product*: a
photoreal viewer, not a twin, because the lenses cannot follow into a mesh with no buildings in it.

⚠️ Before any such prototype, **check Google photoreal coverage per AOI**. Coverage and capture
quality vary, and a science campus on a city's edge is not a city centre.



---

## 6. Cost, concretely

Assume a demo session pulls ~2,000 3D tiles (conservative for a few minutes of flying).

| Scenario | Option A (ion Commercial) | Option B (direct Google) |
|---|---|---|
| 1 demo/month | $149 | ~$6 (first 1,000 free) |
| 20 demos/month | $149 | ~$234 |
| 100 demos/month | $149 (quota permitting) | ~$1,194 |
| Left running overnight in a tab | $149 | **unbounded** |

The flat fee wins the moment you demo more than about ten times a month, and it removes the
tail risk entirely. **That is the real argument for ion over direct Google** — not the features.

---

## 7. Recommendation

**For internal demos and prototypes:** keep the ion Community token.
It sits inside the "exploratory commercial development" carve-out. Two hygiene fixes:

1. **Restrict the token** in the ion dashboard to the specific asset IDs and your app's hosting
   domain. Right now anyone reading the bundle can spend your quota.
2. Add a one-line note in each demo README saying the token is evaluation-scope only, so nobody
   copies it into something that ships.

**The moment anything ships for real** — someone else's tenant, real users, a public URL — pick one:

- **Photorealism is the point** (harbour, airport, campus fly-throughs, the executive wow):
  buy **ion Commercial ($149/mo)** and talk to Cesium about the "outside your organization"
  clause. Do **not** quietly switch to a direct Google key to dodge the fee — you'd move a
  $149 flat cost onto an uncapped meter *and* introduce a third-party cloud bill into a project
  that didn't have one.
- **Photorealism is nice-to-have** (most operational dashboards, and essentially every German
  public-sector conversation): go **Option D** — LoD2 buildings + DOP20 orthophotos from the state
  surveying office + Copernicus terrain, baked to static files in OneLake/Azure. Free, officially
  licensed for commercial use, no runtime dependency on anyone. **This is already built** — reuse
  the existing `tools/geodata/` pipeline rather than starting again. Add **Option E (Azure Maps)**
  only when you need coverage outside Germany; it is not free and it is not needed inside Germany.

> ⚠️ **"Just use OpenStreetMap instead" does not work as a substitute for imagery.** OSM is a
> *vector map database* — it contains no aerial photography at all. Swapping a satellite layer for
> OSM raster tiles gives you a road map with labels, not a photographed ground, and the app stops
> looking like a twin. The free-and-valid imagery answer in Germany is **DOP20**, not OSM.

**Architecturally, copy Harbour Pulse's pattern regardless.** The single-flag fork is the reusable
idea: one env var, photoreal when it's there, honest degradation when it isn't. It means the
same codebase can serve an internal wow-demo and a licence-clean production deployment with no
code change — and it means a missing or revoked token never produces a blank screen.

---

## 8. Open questions to confirm before committing to a stack

- Whether an existing enterprise agreement **already covers Google Maps Platform** anywhere, if
  Option B is ever seriously considered (assume not).
- Exact wording Cesium applies to **"solutions used outside your organization"** for an app
  running in someone else's Fabric tenant — this needs Cesium sales, not the website.
- Whether **Azure Maps satellite imagery** may be re-projected onto a Cesium globe under the
  Azure Maps terms (raster tiles into a third-party renderer is not obviously in scope).
- Whether Bentley ownership changes ion's licensing or pricing — worth re-checking annually.

---

## References

- Cesium ion pricing & FAQ — https://cesium.com/platform/cesium-ion/pricing/
- Cesium company history — https://cesium.com/about/ · https://cesium.com/press/
- CesiumJS licence (Apache-2.0) — https://github.com/CesiumGS/cesium/blob/main/LICENSE.md
- Bentley acquisition of Cesium GS (Sept 2024) — https://en.wikipedia.org/wiki/Bentley_Systems
- Google Maps Platform price list — https://developers.google.com/maps/billing-and-pricing/pricing
- Google SKU billable events — https://developers.google.com/maps/billing-and-pricing/sku-details
- Photorealistic 3D Tiles overview — https://developers.google.com/maps/documentation/tile/3d-tiles-overview
- OSMF Tile Usage Policy — https://operations.osmfoundation.org/policies/tiles/
