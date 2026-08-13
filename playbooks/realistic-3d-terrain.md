# Realistic 3D terrain in the browser — a reusable playbook

> Working notes, distilled from building a 13 km flood twin (three.js + WebGL2, ~47 MB payload,
> 16.7 ms frame on an integrated Adreno X1-85). Area-agnostic. Written for myself, shared as-is —
> the 🔴 items are the ones that cost me a day or more.

## What actually buys realism, in order of effect
1. **Hillshade.** Without it terrain is an unreadable pale mass. Central differences on the heightmap
   in the vertex shader, low NW sun (cartographic convention). Biggest single win.
2. **Land cover colour.** Bare elevation shading reads as bare stone. Tint by class, don't replace —
   relief must stay readable through it.
3. **Buildings** (real cadastre), then **trees**, then road network. Villages need a base tone clearly
   darker than terrain or they read as texture, not fabric.
4. **True scale.** Exaggeration is the fastest way to look fake. See below.

## Data acquisition (German states; the pattern generalises)
- **Terrain DGM1 / surface DOM1 / LoD2 CityGML / DOP20 orthophotos** — state survey offices, open data,
  `dl-de/by-2-0`. RLP: `geobasis-rlp.de`; NRW: `opengeodata.nrw.de`. CRS **EPSG:25832 (UTM32)**.
- **Metalink catalogue pattern** (RLP, likely others): product JSON → `.meta4` catalogue (size + SHA-256
  per tile) → tile URLs. DGM/DOM tiles **1 km**, LoD2 tiles **2 km** — a radius sized for 1 km silently
  misses neighbours (I got 41 buildings instead of 307).
- **OSM via Overpass** for land cover, roads, buildings, place nodes, watercourses. Use **≥3 mirrors +
  retries with backoff** (overpass-api.de, kumi.systems, private.coffee, osm.ch) — a full pipeline run
  earns 504s. Counts differ slightly between runs/mirrors; not a bug.
- ⚠️ **`out geom` returns the WHOLE geometry of any way intersecting the bbox** → clip to the AOI yourself.
- German geoportals move URLs constantly: start at the authority root, don't deep-link products.
- ⚠️ **Check the acquisition year.** Open DGM is usually "current" only; for a past event you are
  rendering post-event terrain. State it in the UI, never silently correct.
- **No GDAL / pyproj / rasterio needed**: numpy + pillow + scipy + stdlib (`urllib`, `struct`, `xml`) is
  enough. PIL reads float32 GeoTIFF; shapefiles parse with `struct`; write your own Transverse Mercator.

## Registration — how to prove the map is correctly placed
- 🔴 **The best check is a river bed profile**, not village coordinates. OSM georeferences the centreline
  independently of the DGM, and the bed is the valley's lowest point, so any mis-registration pushes the
  sampled profile up the sides. Mine fell **173.5 → 88.5 m over 24.6 km, strictly monotonic**, and matched
  the official gauge datum to **0.7 m** — that confirms horizontal *and* vertical registration at once.
- **Corroborate land-cover rasters with facts that fall OUT of the data**: vineyard area vs the published
  wine-region area; vineyard = steepest class; railway = lowest class. A flip or offset breaks all three.
- ⚠️ **Never verify with recalled coordinates.** In a gorge, 200 m horizontal error ⇒ ~150 m vertical
  error; my "errors up to 166 m" were my own bad lat/lons. Use OSM place nodes, and cross-check against
  per-village building ground medians.

## Terrain
- Heightmap **uint16, 4 m posting** (`h = min + raw*scale`), plus a **nodata mask**.
- 🔴 **Rasters are row 0 = NORTH; `PlaneGeometry` uv v=0 lands SOUTH after `rotateX(-PI/2)`** → sample
  with `vec2(u, 1.0 - v)` or the whole map is mirrored. *(A mirror is quiet: an E–W valley reflected about
  the middle of its own box leaves the valley in the middle and the towns near the towns.)*
- 🔴 **Fill nodata nearest-neighbour, never with a constant or the minimum.** Constant = cliff wall at the
  state border; minimum = permanent lake. Carry the mask so filled cells can never be "wet".
- Render mesh: decimate the grid (4× → 16 m posting, ~470 k verts). One vertex per heightmap cell
  is 7.5 M — far too many, and invisible at normal camera range.
- **Exposure: keep `ambient + gain*lambert <= 1.0`.** `0.62 + 0.52*lambert` peaks at 1.14 and clips
  sunlit slopes to pure white ("plaster" look). `0.58 + 0.42*lambert` is safe.

## Vertical exaggeration — default to 1
- 🔴 **True scale by default.** Any factor > 1 is a claim the survey does not make. Offer it as a toggle.
  History here: 2.5 → 1.5 → 1. The 2.5 was sized on a *wrong* comment about the relief.
- **Check the real relief before choosing a factor.** 429 m of relief over 13 km at 2.5× renders >1 km of
  apparent relief = alpine. Print the actual range in the UI ("88–517 m ü. NHN").
- Exaggeration must be **render-only**: apply it to `displaced.y` and the shading normal, keep `vTerrainZ`
  in real metres so any physics (`depth = wse - z`) never sees it. `grep exagger tools/**` should be empty.
- ⚠️ **Do NOT scale building/tree height by it** — it turns houses into towers. Pass per-vertex or
  per-instance `aGround` and do `y = ground*exag + (y - ground)*1.35`. Mixed scales also make buildings
  look too small against hills, which compounds a "mountains too high" impression.
- 🔴 **If exaggeration is switchable, rebuild instanced bounding spheres** (`center.y = mid*f`,
  `radius = base + halfSpread*f`) or whole hillsides blink out at the frustum edge.
- Scale the **camera position and controls target by the ratio** too, else the view lurches.

## Buildings (LoD2)
- 🔴 **Quantise the mesh, planar**: int16 x/z @0.25 m + uint16 y @0.01 m above an offset, written as three
  blocks so the browser wraps each with no copy. **60 MB → 26 MB.** Keep a float32 fallback path keyed on
  a `quantisation` block in the metadata.
- Clip to the terrain extent (a 2 km tile band reaches past the AOI and those buildings have no ground
  under them) and drop tiny footprints (`--min-footprint 20 m²` removed 2 677 sheds).
- Per-building dynamic colour: a 1-D `DataTexture` keyed by building index + an `aBuilding` vertex
  attribute. Recolours 12 k buildings per frame with zero geometry work.
- 🔴 **Any per-item `DataTexture` must wrap into rows once items can exceed 16 384.** A `30207 × 1` strip
  exceeded `MAX_TEXTURE_SIZE` on an integrated GPU, the upload failed **silently** (`GL_INVALID_VALUE`,
  nothing thrown), every sample returned 0, and every building rendered the ramp's "dry" colour. Use a
  fixed width (2048 = the WebGL2 guaranteed minimum) and unwrap with `mod`/`floor` in the shader.
- Move footprint rings to an **offline-only** JSON; the app doesn't need them (6.2 → 1.04 MB).

## Vegetation (real trees from DOM − DGM)
- **nDOM = DOM1 − DGM1**, keep 3–48 m, tree tops = local maxima (`maximum_filter`, size = spacing).
  Remove buildings twice: OSM footprint discs (`r = sqrt(area/π)*1.6`) **and** roughness (local σ over 5 m
  ≥ 0.55 m — a roof is a plane, a crown is rough).
- `--spacing 10 m` ⇒ ~390 k trees at **9 bytes each** (`<hhHBBB`: int16 x, int16 z, uint16 ground dm,
  uint8 height 0.2 m, uint8 crown radius dm, uint8 shape). Spacing 7 ⇒ ~700 k, too many.
- 🔴 **The performance answer is CHUNKING, not geometry.** One `InstancedMesh` per ~1 km cell with its own
  bounding sphere ⇒ frustum culls most of the wood. 274 chunks, 16.7 ms. A single mesh submits everything
  every frame. At 390 k trees triangle count was **never** the bottleneck — 12-tri and 30-tri crowns
  measured identical. Don't optimise geometry without measuring.
- **Two crown forms beat one.** Conifer 24 tri (3 tiers) + broadleaf 30 tri (rounded), both on a 3-sided
  trunk, from one `lathe(profile, sides)` helper. **Random Y rotation per tree** (stable hash) is free and
  kills the "stamped wood" look. Bucket chunks by `species:chunkX:chunkZ`.
- 🔴 **Derive the form from the data, don't assign it.** Sample nDOM on rings 1–8 m around each apex;
  crown radius = where canopy falls to 45 % of apex; taper = canopy at 0.18×height. Taper < 0.62 ⇒ conical.
  **Validate the classifier**: neighbours of a conifer were 47.1 % conifer vs a 20.5 % base rate, and a
  **shuffled-label control gave 20.5/20.5** ⇒ the clustering is real (planted stands). Call it crown
  **form**, not species. OSM `leaf_type` doesn't help here (117/183 polygons untagged, zero needleleaved).

## Land cover + roads (class raster)
- Rasterise OSM polygons with **PIL `ImageDraw.polygon`** (no GDAL). **Paint largest area first** so small
  polygons survive; relation inner rings painted back to class 0. Roads last, ascending importance.
- The grid must mirror the heightmap extent exactly so a uv means the same place in both.
- 🔴 **Line width is where "pixly" comes from**: `width = round(width_m / resolution)`. At 8 m *every* road
  rounds to 1 cell, so a 4 m service road and a 13 m primary are both drawn 8 m wide. **Use 2 m.**
- 🔴 **Class rasters gzip ~27:1** (28.6 MB grid → **1.06 MB** on the wire — *less* than an 8 m raster raw).
  Inflate cost 121 ms. **Finer map = smaller download.** This is what makes 2 m affordable.
- ⚠️ **Never name a pre-compressed asset `.gz`.** Vite sets `Content-Encoding: gzip` on it (the browser
  inflates transparently, then your own inflate throws); other static hosts set nothing and hand over raw
  bytes. Same file, opposite behaviour. Use a neutral extension (`.u8z`) and **detect by content: `1f 8b`
  magic**. Check the inflated length against `width*height` before uploading to the GPU.
- Put the raster **filename and resolution in a fixed-name descriptor JSON**, so a resolution change needs
  no app change. Have the builder delete superseded rasters (the old grid keeps shipping otherwise).
- 🔴 **Invisible line features are usually a COLOUR problem, not resolution.** I blamed jitter first and
  **measured myself wrong** — 89.1 % of road fragments still sampled a road. The real cause: one grey for
  all roads, and unpaved track (`0.66,0.63,0.57`) sat on farmland (`0.76,0.72,0.57`). Fix = split
  paved/unpaved from the OSM `surface` tag (58 % coverage; fall back to class habit). Asphalt is darker
  than any ground, gravel paler than any — one shared grey guarantees one of them vanishes.
- **Hash-jitter the class lookup by ±½ cell** so field edges are ragged instead of staircased — but
  **exempt line classes in both directions** (a road sample wins; a jittered sample landing on a road falls
  back), else it eats the line or smears it onto roadless ground.
- Keep the palette muted and **reserve saturation/darkness for the thing that matters**.
- ⚠️ Don't invent sub-cell detail (vineyard row stripes at real 1.8 m spacing would alias, and an invented
  spacing is unearned detail).

## Rendering gotchas
- 🔴 **A custom-shader scene has NO lights.** Terrain/buildings/trees each bake their own shading, so a
  `MeshLambertMaterial` renders **black**. Repeat the same sun vector in every material.
- `instanceMatrix`/`instanceColor` are auto-declared by three for `ShaderMaterial` (not `RawShaderMaterial`)
  on an `InstancedMesh`.
- A `usampler2D` uniform **must still be bound** when the raster is absent, or it reads texture unit 0.
- `OrbitControls`: damping 0.08, rotateSpeed 0.55, zoomSpeed 0.7, `maxPolarAngle = PI*0.48` (stops the
  camera dropping under the terrain). `frame()` must set **`controls.target` too** or the next drag snaps.
- 🔴 **The plane is flat until the vertex shader displaces it**, so three.js culls the ground as soon as the
  camera drops below the ridge → `terrain.frustumCulled = false`.

## Camera
- **One mesh, many places.** Place buttons should only move the camera. But an instant cut across
  continuous terrain is **indistinguishable from loading a different map** (a user reported exactly that).
  Ease over ~1500 ms with a half-sine lift (`min(distance*0.25, 2600 m)`); the apex shows the continuity.
  Honour `prefers-reduced-motion`, skip moves < 50 m, cancel on the controls `start` event.

## Payload and loading
- ~47 MB before anything renders ⇒ **you need a real progress indicator**, and the dead-looking UI around
  it matters as much: hide the control panel until ready, or the page reads as broken rather than busy.
- ⚠️ **Never size a progress bar from `Content-Length`.** Many static hosts answer
  `Transfer-Encoding: chunked` with no length — header-driven bars work on the dev server and are
  permanently indeterminate in production. Behind gzip the header is the compressed length anyway.
- ✅ **Derive expected bytes from metadata you already fetched** — raster `w*h*bytesPerCell`, mesh
  `vertices*6`, trees `count*stride`. Verified byte-exact on all six binaries. No manifest to go stale.
- **Declare every expected size BEFORE fetching any payload.** Reading one descriptor lazily grew the
  stage total mid-flight and the bar ran **backwards 97 % → 90 %**.
- Throttle progress emits to ~100 ms (a 26 MB body arrives in hundreds of chunks).

## Verifying rendered output — this is where the bugs are
- 🔴 **Colour-classifying pixel tests are a trap.** "Count turbid-brown pixels" broke twice — first when
  trees were added (sunlit canopy also has r > b), then again when vineyard ochre arrived. **Capture a
  dry/base frame and measure the DIFFERENCE**: palette-immune, and it traced the hydrograph properly.
- ⚡ **Keep frame comparisons inside the browser** (`window.__frames` slots, return one number). Returning a
  1280×800 frame is 3 M numbers over CDP; fixing that took one spec from **2.0 min → 40 s**.
- The renderer needs **`preserveDrawingBuffer: true`** or `readPixels` always returns zeroes.
- **Screenshot diffing cannot verify camera motion** if anything animates per frame (e.g. water `uTime`).
  Hash a clip of static hillside instead.
- Verify overlays don't cover panels by **measuring `getBoundingClientRect` intersections**, and make the
  check **throw if a panel testid is missing** — mine silently matched nothing and passed vacuously.

> 🔴 **The lesson that outranks all the fixes:** `tsc` + 54 unit tests + 57 e2e + eslint were ALL GREEN
> while the app rendered an entire valley wrong. Anything that only fails as a *fetched filename* or a
> *rendered pixel* survives the whole verify chain. After every deploy, actually open the thing and look.

## Playwright + heavy WebGL
- 🔴 **Root cause of every "WebGL spec is flaky/slow": headless Chromium rasterises with SwiftShader on the
  CPU.** Measured: median frame **884 ms**, and a trivial `page.evaluate` took 0.5–8.7 s because rendering
  blocks the main thread. Fix in `launchOptions`:
  `args: ['--use-angle=default','--enable-gpu','--ignore-gpu-blocklist']` + `ignoreDefaultArgs: ['--disable-gpu']`
  → frame **884 → 16 ms**, suite **11.6 min with 2 failures → 24 s green**. Safe unconditionally (falls back
  to SwiftShader when there is no GPU). Confirm via `WEBGL_debug_renderer_info` — "SwiftShader" = bad.
  ⚠️ Do **not** reach for `workers: 1` / serial mode first; that treats the symptom.
- ⚠️ **Never assert animation progress after a FIXED wait.** rAF-driven clocks only advance when frames
  arrive, and parallel workers share one GPU. Use `expect.poll` with a 30–40 s budget.
- Every `page.mouse.move` forces a render → keep drags to ≤10 moves; coordinates must stay in the viewport.
- `@types/three` is a required devDependency.
