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
| **Pricing / utilisation** | 🟡 real, and quantifiable | "The app barely uses CU. The thing to plan for is that it's always on — so the capacity behind it needs to be too." |

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

## 3 · Pricing / capacity utilisation — 🟡 real, and quantifiable

### The sharp version
A Fabric App is **remarkably cheap to run**. The thing to plan for is that it's **always on**, and
the capacity behind it has to be too.

A paused capacity means the app doesn't answer: root serves `HTTP 500`, lazy chunks 500, UDF invokes
500. `rayfin up` returns `404 The requested endpoint does not exist` before it ever surfaces
`CapacityNotActive`. After a resume it serves 408s for another 20–30 s while the workload warms.
All of that is consistent — it's simply what "the capacity is off" looks like from the browser.

**So hosting an app turns a schedulable capacity into a 24/7 one. That's a sizing decision, and it's
worth making deliberately rather than discovering it on the invoice.**

### The evidence — two capacities, one tenant, same week

| | hosts Fabric Apps | hosts none |
|---|---|---|
| Uptime | **91 %** | **26 %** |
| Cost that week | **$714.53** (74 % of all Azure spend) | $196.33 |

Same owner, same schedule, same Logic Apps. **The app is the entire difference.** The daily 18:00
pause is undone within minutes, every day, because the app has to answer.

### The arithmetic
```
capacity-hours   = CU-seconds / (SKU CU × 3600)
utilisation      = capacity-hours used / hours the capacity was Active
unpausable hours = hours × (uptime_with_app − uptime_without_app)
cost of the pause you can't take = unpausable hours × SKU CU × rate
```

On a typical small app (200 users, Direct Lake, ~12 opening queries, 3 % concurrency): peak
**0.35 CU** → fits an **F2**. Put that same app on an F32 and roughly **$2,885/month** of the bill is
buying uptime you'd otherwise have paused, at an effective **$3,635 per CU-hour actually used**
versus $0.19 list. The lesson isn't "apps are expensive" — it's **size the capacity to the app, and
the economics are excellent**.

✅ **If the workload already runs a 24/7 capacity for other reasons**, the marginal cost of the app is
near zero — say so. That's the common case, and it's where this question disappears entirely.
