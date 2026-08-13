# The drone camera — one file, eight apps, two renderers

> How `flyControls.ts` works, why it has no toggle button, and how to port it.
> Companion to the code: the Three.js version ships inside the **paragliding-insights** template in
> `microsoft/awesome-rayfin` (PR #92); the Cesium port is on a public fork of Harbour Pulse.

---

## Why there is no "drone mode" button

OrbitControls and a free-flight camera want the **same four inputs**. Counted precisely, there are
four collisions — not one:

| input | OrbitControls | drone |
|---|---|---|
| left drag | rotate around target | look |
| wheel | dolly zoom | cruise speed |
| Shift + left drag | **pan** (it binds ctrl/meta/shift on LEFT) | boost |
| arrow keys | pan | look |

Free: `W A S D Q E R F`, middle/right button, all touch gestures.

So the merge isn't a mode switch — it's **deciding which behaviour the viewer is doing** and binding
the four contested inputs accordingly. And that decision is a **latch**, not a toggle:

- not engaged → the map. Drag orbits, wheel zooms. Unchanged for anyone who never flies.
- press `W A S D Q E R F` → engaged. Drag looks, wheel is the throttle.
- **1 s** with no movement key and no drag → hands back **in place**.

⚠️ **Do not define "flying" as `velocity > 0`.** Meaning that changes on a timer the user didn't set
is a mode error. The grace window *is* the design.

**What replaced the button** — and why it couldn't just be deleted: the merge changes what the wheel
and the drag *do*, so something must say (a) that the keys exist and (b) which behaviour the mouse
currently has. Two shapes work: one element with `data-flying="true|false"` whose text swaps
hint ↔ help, or a `drone-hint` that becomes a HUD while flying (the HUD appearing *is* the
statement). Use `data-flying`, not `aria-pressed` — the latter would be a lie about something
unpressable.

---

## The hand-back — the bug this fixes

🔴 **`OrbitControls.update()` clamps `phi` to `[minPolarAngle, maxPolarAngle]` unconditionally, every
frame, and enforces it by *moving the camera*.** So deriving the orbit target as
`camera.position + viewDir * D` snaps the camera whenever the view is level or pitched up — with
`maxPolarAngle = 0.48π` that's any view pitched up more than about **−3.6°**, i.e. nearly all of them.

**This bug was in every app that had free flight, from the day it landed.**

`handBackToOrbit()` fixes it in three steps:
1. **Clamp the pitch** just below the limit, keeping the bearing.
2. **March the view ray against the ground** (48 steps + 8 bisections) so the orbit centre lands on
   the terrain the viewer was actually looking at.
3. **Clamp the distance** into `[minDistance × 1.05, maxDistance × 0.95]` — a distant ridge is
   further than `maxDistance` and would clamp too.

Measured hand-back jump after the fix: **0.000 m**.

---

## Keeping one file across many apps

The module is **byte-identical in 8 Three.js apps** (verify with `Get-FileHash`). That only works
because of one discipline:

> **Every app-specific number is an option. Every app-specific fact lives in the host scene.**

Real per-app options in use:
```
defaults, no inertia                                   (a flood twin)
cruise 25 / 900 / 180, boost 3, taus 0.28/0.16/0.07    (paragliding, campus twins)
cruise 8 / 400 / 60, boost 3, referenceAglM 25,
  aglScaleMin 0.3, aglScaleMax 14, handoffDistanceM 3000   (a maritime twin)
```
That last one is the interesting case: its reference height is a **mast top**, not a building, so the
2.6× headroom every other app uses was far too little — **that is why the AGL scaling range had to
become an option at all** rather than a constant.

---

## Porting it (Three.js)

1. Copy `flyControls.ts` into `src/twin3d/`. Delete the app's old drone camera **and its test**.
2. Build the scene once; pass `controls` (a structural `OrbitLike` — works with OrbitControls,
   MapControls, a fork, or a stub) and an optional `groundAt`. In the render loop swap
   `if (drone.enabled) drone.update(dt)` → `if (fly.engaged) fly.update(dt)`.
3. Expose `setEngaged`, `engaged`, `cruiseMs` **and an `onEngagedChange` subscription** — the UI must
   *follow* the latch, not command it.
4. `onEngagedChange(true)` must cancel **everything else that drives the camera**: in-flight
   transitions, guided tours, follow-target modes.
5. The UI toggle only *asks* (`onToggle={next => handle.setFreeFly(next)}`); state comes from the
   subscription. Add an idle hint ("Or just press W A S D") — **without it the merge is invisible**.
6. Copy the unit tests (53 of them) and the hand-back e2e tests.

⚠️ **`groundAt` must return the DRAWN elevation.** If your app renders with vertical exaggeration,
multiply — it is compared against `camera.position.y`.

---

## Porting it to Cesium

Same behavioural model, **rewritten against the Cesium camera API — not a copy**. Four traps, all
found the hard way:

- 🔴 **Cesium's event-type names are inverted vs intuition.** In 3D, `rotateEventTypes` carries you
  *across* the globe (that's the **pan**) and `tiltEventTypes` swings around the picked point (that's
  the **orbit**). Binding by name gets it exactly backwards. **Bind by behaviour, then measure.**
- 🔴 **`lookEventTypes = []` is mandatory.** Cesium binds free-look to Shift+left by default — the
  same chord as pan — and the two fight, yawing the view.
- 🔴 **There is no `maxPolarAngle` equivalent.** A long drag sails over the zenith and leaves the
  camera **heading 180 / roll 180 — silently inverted**, and every later drag reads mirrored. Fix
  with a `scene.preRender` guard holding the last legal pose (pitch −89.5°…−3.6°, |roll| ≤ 1°) and
  `setView`-ing back on the first illegal frame. Skip the guard while the drone is engaged (a pilot
  legitimately pitches up and rolls); on hand-back, clamp to the nearest bound.
- 🔴 **A `flyTo` requested while the latch is engaged is impossible** — `applyOrientation()` runs
  every frame and overrides it. **Hand back *before* flying.**
- ⚠️ If you have a basemap/imagery toggle that **destroys and rebuilds the Viewer**, re-attach
  flyControls inside that effect or the drone silently dies after the first switch.

Sensitivity needs no tuning: Cesium's tilt already matches `rotateSpeed 0.55` (140 px → 54° measured
vs 59° predicted). Drive it with
`viewer.scene.preUpdate.addEventListener(() => fly.update(dt))`, dt clamped to 0.1 s, and
`fly.dispose()` in cleanup.

---

## Testing it — three traps that cost real time

- ⚠️ **Never measure camera speed through a degraded browser session.** The same code gave 146 m
  early in a session and 12 m later, once WebGL was exhausted and the scene ran at 1–2 fps. The
  0.1 s **dt clamp** then dominates: one frame moves `BASE × BOOST × 0.1`, so you measure
  frame-count quantisation, not your setting. A boost of 12 read back as 5.1.
  **Verify constants by reading the deployed bundle instead.**
- ⚠️ **Synthetic keydown + a stray blur.** The controls clear `held` on `blur`, and a test harness
  tearing down a previous context can steal focus between the press and the first poll → the camera
  never moves, the assertion reads 0, and it passes when run alone. **Re-dispatch the keydown on
  every poll** (`held` is a Set, so repeats are free).
- ⚠️ **With inertia, "keys are up" and "camera has stopped" are ~1.2 s apart.** Waiting a fixed
  700 ms fails by half a metre. Sampling the camera for two equal values is *also* wrong — equal
  samples can mean *no frame was drawn*. **Wait on the speed readout reaching 0.**
- ⚠️ A test that must stay engaged while you measure stillness should **hold an arrow key**: it
  resets the idle window every frame and turns the view without moving the camera.

---

## The bit worth saying out loud

The camera costs nothing. `three` is its only import; CesiumJS is Apache-2.0. **The pixels are what
you pay for** — a photorealism token gates the *content*, never the renderer and never the camera.
