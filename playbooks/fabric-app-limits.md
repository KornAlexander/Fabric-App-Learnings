# Fabric Apps — the three standing limitations

> What I hit building ~20 Fabric Apps. Written so you don't lose the same days I did.
> Verified 2026-08-12. Everything here is measured, not felt.

**The rule underneath all three:** name the limitation before your audience does. You lose nothing —
they'll find it in week two anyway — and you gain the right to be believed about everything else.

| Limitation | Verdict | The one-line answer |
|---|---|---|
| **Rayfin functions** | 🔴 genuinely blocked | "No server-side Rayfin function today. Use a Fabric User Data Function or an Azure Container App — both proven, both cheap." |
| **The public URL** | 🟡 awkward, not blocked | "The shell is public and the hostname isn't yours. The data is still Entra-gated. If your *layout* is confidential, wait." |
| **Pricing / utilisation** | 🟡 real, and quantifiable | "The app barely uses CU. The problem is it can't be off — so you buy an always-on capacity for a workload using under 1 % of it." |

---

## 1 · Rayfin functions — 🔴 genuinely blocked

- Across **65 `rayfin.yml` files** in my workspace, `functions.enabled` is **`false` in every single
  one**. Not one app uses them. That isn't taste; it's the state of the feature.
- The semantic-model connector fails with a specific, non-actionable error:
  > `ConnectorFunction invocation is not enabled for this workspace`
- ⚠️ **It is not a config mistake and there is no setting to flip.** In my case `rayfin up` reported
  *"Runtime settings applied"*, the `rayfin.yml` was valid (`version: "1"` **and**
  `auth: {type: delegated}`), **all 169 tenant settings were scanned** — only `AppBackendTenant` and
  `EnableAnonymousDataAccessForFabricApps` exist, and neither is it. **No Learn doc covers it.**
  That cost a day.

### Two proven escape hatches

| Route | Language | Use it when |
|---|---|---|
| **Fabric User Data Function**, invoked by REST | Python | short request/response, stays inside Fabric, no extra Azure resource |
| **Azure Container App** | anything | long CPU work, native binaries, or holding a connection open |

**Why some apps genuinely had to use a container** — these are the real reasons, not preferences:
- A CP-SAT (OR-Tools) solver needs seconds-to-minutes of CPU and a native binary:
  *"must not run in a browser or a Fabric UDF timeout window."*
- A live AIS feed: *"a container holds the upstream socket open, which a request-scoped function
  cannot."*
- Any Foundry-agent chat assistant, because the browser cannot hold a credential.

### The cost objection, pre-empted
*"So now I need Azure too?"* — yes, and it's noise. Measured over six days on my tenant:
**Container Apps + ACR = $4.56**, i.e. **0.5 %** of Azure spend. Fabric capacity was **94.6 %**.
The escape hatch is never what costs money.

---

## 2 · The public URL — 🟡 awkward, not blocked

**Four separate issues get bundled into "the public URL problem". Separate them or the conversation
goes nowhere.**

### 2.1 The shell is genuinely public
A plain `GET` on the app root — and on `/assets/index-*.js` — returns **200 to anyone**.
- **App shell = public. App data = Entra-gated.** Defensible, but *not* what people assume when they
  see a Fabric sign-in screen.
- Everything in `public/` ships. Every `VITE_*` value is in the bundle. An `X-App-Key` is a speed
  bump, not authentication.
- ⛔ **There is no way to require Entra before the bundle is served.** If your app's *layout* itself
  reveals something confidential, that's a genuine blocker — say so and stop.
- The related dial is **tenant-wide**: `Enable anonymous data access for Fabric Apps (Preview)`.

### 2.2 The hostname isn't yours, and it can change
Format: `https://<adjective>-<noun>-<hash>-<region>.webapp.fabricapps.net`
- **No custom domain. No CNAME. No vanity URL.** The platform owns the hostname.
- **It changes if the binding is lost.** I have one app whose `rayfin.yml` carries *two* hostnames;
  elsewhere a redeploy moved the host and broke sign-in with **`AADSTS50011`**.
- ✅ Stable as long as **`rayfin/.deployments.json` survives** — it binds `fabricItemId` +
  `hostingUrl`, keyed by workspace slug. Lose it, get a new host.
- ⚠️ `rayfin up` **rewrites** `rayfin.yml` and re-adds whatever host it just deployed to. And
  **`staticapp deploy` alone does not re-register redirect URIs** — you need a full `rayfin up`.
- ⚠️ If the app uses **raw MSAL** (not Fabric brokered auth), the new origin must *also* be added to
  the Entra app registration's SPA `redirectUris` **by hand**. `rayfin.yml`'s `allowedRedirectUris`
  is a Fabric setting — **it does not touch Entra.**

### 2.3 🔴 Check what's in your `.deployments.json`
That file contains a **`publishableKey`** plus tenant/workspace/item IDs — and in my repos it's
**committed in some and gitignored in others**. Decide the convention once, before anything goes
public. Right now my own repos disagree with each other, which is exactly how this leaks.

### 2.4 You cannot un-publish
`rayfin up` **never deletes**. Removing a file locally and redeploying is **not** a withdrawal — the
old path keeps serving its old bytes (verified with a cache-busting query string, so it's the host,
not a CDN). The only withdrawal is publishing a **tombstone** over the same path.

> 🔴 **The story that makes this concrete.** One of my apps had a `public/*.json` pairing a cadastral
> ID, an exact building footprint, a building function and a damage grade for **2,080 real
> buildings** — answering **HTTP 200 to anyone**. A source comment said those fields *"never reach
> the client"*. True of the UI. False of the deploy. **Vite copies `public/` → `dist/`.**
>
> Two rules out of it: *anything your governance rules forbid showing must not sit under `public/`*,
> and *deleting it locally is not removing it*.

⚠️ **Bonus trap:** every Fabric static host is an **SPA catch-all** — any unknown path returns
`index.html` with **HTTP 200**. So "the URL works" proves nothing. Check the `<title>`. This is how
I caught two wrong demo URLs the day before a talk.

---

## 3 · Pricing / low capacity utilisation — 🟡 real, and quantifiable

### The sharp version
The problem is **not** that a Fabric App burns CU. **It's that it can't be off.**

A paused capacity makes the app **dead**: root serves `HTTP 500`, lazy chunks 500, UDF invokes 500.
`rayfin up` fails with `404 The requested endpoint does not exist` before it ever surfaces
`CapacityNotActive`. After a resume it serves 408s for another 20–30 s while the workload warms.

**So hosting an app converts a schedulable capacity into a 24/7 one, and every cost lever the
platform gives you is precisely the thing that breaks it.**

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
**0.35 CU** → fits an **F2**. On an F32 you'd be paying **~$2,885/month for a pause you're not
allowed to take**, at an effective **$3,635 per CU-hour actually used** versus $0.19 list.

⚠️ **If the workload already runs a 24/7 capacity for other reasons**, the marginal cost of the app
really is near zero — say so. That's the case where this objection evaporates entirely.
