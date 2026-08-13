# Fabric Apps — three things to plan for

> What I ran into building ~20 Fabric Apps, and how I designed around each one.
> Verified 2026-08-12. Everything here is measured, not felt.

Fabric Apps are a genuinely good way to put a real interface on a semantic model — the platform does
the hosting, the identity and the data path for you, which is most of the work. These three points
are the ones worth knowing up front so you design with them rather than discover them late.

**The rule underneath all three:** name the constraint before your audience does. You lose nothing —
they'll find it in week two anyway — and you gain the right to be believed about everything else.

| Topic | Status | The one-line answer |
|---|---|---|
| **Rayfin functions** | 🟡 not there yet | "Server-side Rayfin functions aren't available yet. Use a Fabric User Data Function or an Azure Container App — both proven, both cheap." |
| **The public URL** | 🟡 by design — design around it | "The shell is served publicly and the hostname is platform-owned. The data stays Entra-gated. If your *layout* itself is confidential, pick a different surface." |
| **Capacity sizing** | 🟡 worth doing once, properly | "The app itself barely uses CU — a typical small one peaks at 0.35 CU and fits an F2. Size the capacity to the workload and it's very cheap." |

---

## 1 · Rayfin functions — 🟡 not there yet

- Across **65 `rayfin.yml` files** in my workspace, `functions.enabled` is **`false` in every single
  one**. Not one app uses them — the capability simply isn't available to me yet.
- The semantic-model connector says so directly:
  > `ConnectorFunction invocation is not enabled for this workspace`
- ⚠️ **It isn't a config mistake, and there's no setting to flip.** In my case `rayfin up` reported
  *"Runtime settings applied"*, the `rayfin.yml` was valid (`version: "1"` **and**
  `auth: {type: delegated}`), and **all 169 tenant settings were scanned** — only `AppBackendTenant`
  and `EnableAnonymousDataAccessForFabricApps` exist, and neither is this. Worth knowing before you
  go looking: I spent a day on it so you don't have to.

### Two proven routes that work today

| Route | Language | Use it when |
|---|---|---|
| **Fabric User Data Function**, invoked by REST | Python | short request/response, stays inside Fabric, no extra Azure resource |
| **Azure Container App** | anything | long CPU work, native binaries, or holding a connection open |

**Why some apps are a natural fit for a container anyway** — these are real architectural reasons,
not workarounds:
- A CP-SAT (OR-Tools) solver needs seconds-to-minutes of CPU and a native binary:
  *"must not run in a browser or a Fabric UDF timeout window."*
- A live AIS feed: *"a container holds the upstream socket open, which a request-scoped function
  cannot."*
- Any Foundry-agent chat assistant, because the browser cannot hold a credential.

### The cost question, answered up front
*"So now I need Azure too?"* — yes, and it barely registers. Measured over six days on my tenant:
**Container Apps + ACR = $4.56**, i.e. **0.5 %** of Azure spend. Fabric capacity was **94.6 %**.
The extra component is never what costs money.

---

## 2 · The public URL — 🟡 by design, so design around it

**Four separate things get bundled into "the public URL problem". Separate them and each one has a
clear answer.**

### 2.1 The shell is served publicly
A plain `GET` on the app root — and on `/assets/index-*.js` — returns **200 to anyone**.
- **App shell = public. App data = Entra-gated.** That's a sensible split for a static host, but it
  is *not* what people assume when they see a Fabric sign-in screen — so say it out loud.
- Everything in `public/` ships. Every `VITE_*` value is in the bundle. An `X-App-Key` is a speed
  bump, not authentication.
- ℹ️ **The bundle is served before sign-in.** If your app's *layout itself* reveals something
  confidential, that's the signal to choose a different surface — the data gating won't help you
  there.
- The related dial is **tenant-wide**: `Enable anonymous data access for Fabric Apps (Preview)`.

### 2.2 The hostname is platform-owned
Format: `https://<adjective>-<noun>-<hash>-<region>.webapp.fabricapps.net`
- **No custom domain or CNAME today.** The platform owns the hostname, which is also why you get
  TLS and hosting for free.
- **It can change if the binding is lost.** I have one app whose `rayfin.yml` carries *two*
  hostnames; elsewhere a redeploy moved the host and broke sign-in with **`AADSTS50011`**.
- ✅ Stable as long as **`rayfin/.deployments.json` survives** — it binds `fabricItemId` +
  `hostingUrl`, keyed by workspace slug. Keep that file and the host keeps its name.
- ⚠️ `rayfin up` **rewrites** `rayfin.yml` and re-adds whatever host it just deployed to. And
  **`staticapp deploy` alone does not re-register redirect URIs** — you need a full `rayfin up`.
- ⚠️ If the app uses **raw MSAL** (not Fabric brokered auth), the new origin must *also* be added to
  the Entra app registration's SPA `redirectUris` **by hand**. `rayfin.yml`'s `allowedRedirectUris`
  is a Fabric setting — **it does not touch Entra.**

### 2.3 🔴 Decide what belongs in `.deployments.json`
That file contains a **`publishableKey`** plus tenant/workspace/item IDs — and in my repos it's
**committed in some and gitignored in others**. Pick the convention once, before anything goes
public. My own repos disagreed with each other for months, which is exactly how this kind of thing
leaks. This one is on me, not the platform.

### 2.4 Deploys are additive — plan your withdrawals
`rayfin up` **adds and overwrites; it doesn't delete**. Removing a file locally and redeploying is
**not** a withdrawal — the old path keeps serving its old bytes (verified with a cache-busting query
string, so it's the host, not a CDN). To withdraw something, publish a **tombstone** over the same
path.

> 🔴 **The story that makes this concrete — and it was my mistake, not the platform's.** One of my
> apps had a `public/*.json` pairing a cadastral ID, an exact building footprint, a building function
> and a damage grade for **2,080 real buildings** — answering **HTTP 200 to anyone**. A source
> comment said those fields *"never reach the client"*. True of the UI. False of the deploy.
> **Vite copies `public/` → `dist/`.**
>
> Two rules out of it: *anything your governance rules forbid showing must not sit under `public/`*,
> and *deleting it locally is not removing it*.

⚠️ **Worth knowing:** every Fabric static host is an **SPA catch-all** — any unknown path returns
`index.html` with **HTTP 200**. That's correct behaviour for a single-page app, but it means "the URL
returns 200" proves nothing. Check the `<title>`. This is how I caught two stale demo URLs of my own
the day before a talk.

---

## 3 · Capacity sizing — 🟡 worth doing once, properly

### The sharp version
A Fabric App is **remarkably cheap to run**. The front end itself consumes almost nothing — what
shows up on the bill is the queries behind it, and those are the same queries a report would fire.
The only thing worth doing deliberately is **sizing the capacity to the workload** rather than
assuming an app needs a big one.

### The arithmetic
```
capacity-hours = CU-seconds / (SKU CU × 3600)
utilisation    = capacity-hours used / hours the capacity was Active
peak CU        = concurrent users × burst CU / smoothing window (300 s)
```

The number that decides your SKU is **peak CU**, not monthly total. Fabric smooths bursts over a
300-second window, which is why a short spike from a handful of simultaneous users flattens into
something very small.

### What that looks like on a real app
A typical small app — **200 users**, Direct Lake, ~12 queries on open, 3 % concurrency — peaks at
**0.35 CU**. That fits an **F2**, the smallest SKU there is, with room to spare.

That's the headline: an interactive, custom-built front end on analytics-scale data, inside the
smallest capacity Fabric sells. Size it to the workload and the economics are excellent.

✅ **And if a capacity is already running for other reasons** — which is usually the case, since
reports, pipelines and models are sitting on it anyway — the marginal cost of adding an app is
**effectively nothing**. That's the common case, and it's worth saying plainly.

⚠️ Measure rather than trust an estimate: the **Fabric Capacity Metrics** app gives you the real
CU-seconds for your own workload. Anything else, including my calculator, is a rough shape.
