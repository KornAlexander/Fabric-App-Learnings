# Choosing a front end: report, app, or low-code

> A decision guide, not a comparison scorecard. Every option here is a good answer to *some*
> question — the work is knowing which question you have.

## Start here: the front end is not the data strategy

A Power BI report, a Fabric App, a Power App and a Copilot agent can all sit on the **same semantic
model**. That is the part worth internalising before any of the rest:

> **You are choosing a front end, not a data strategy.**

If the model is right — governed, tested, one definition of each measure — then swapping or adding a
front end is a comparatively cheap decision, and you can have more than one. If the model is wrong,
no front end saves you.

---

## The three questions that actually decide it

### 1 · Who maintains this in eighteen months?

The single most predictive question, and it is not technical.

- **Someone who isn't a developer** → Power BI report. It is the only option on this list a analyst
  can pick up cold, and it comes with subscriptions, alerts, Excel export, mobile layouts and usage
  metrics for free.
- **A maker in the business, with governance guardrails** → Power App. Managed Platform gives you
  DLP, Conditional Access, sharing limits and admin telemetry without building any of it.
- **A team that owns a repo** → Fabric App. You get unlimited freedom and you own every consequence,
  including the upgrade path.

> A report is a product with a maintainer. An app is a product with a team.

### 2 · What does the interface have to *do*?

| If the interaction is… | The honest answer |
|---|---|
| Look at numbers, filter, drill, export | **Power BI report.** Don't build an app to reproduce a matrix visual |
| Forms, approvals, transactional write-back with row-level security | **Power App.** Dataverse write-back with security roles is turnkey; on Fabric you build it yourself |
| Something a chart library can't draw — 3D, a map you fly through, a bespoke animation, a game | **Fabric App.** This is the one place the others genuinely cannot follow |
| Drag-and-drop planning, a solver in the loop, undo/redo over a draft | **Fabric App**, and expect to add a container or function for the compute |
| Native mobile, offline, device APIs | **Power App.** Fabric Apps are web/PWA only |

### 3 · How much data, and does it move?

- **Analytics scale, no copy** — millions of rows, reusing DAX measures already defined on the model
  → Fabric App on Direct Lake is very strong here.
- **Transactional, connector-shaped, 1,500 sources** → Power Apps and Dataverse are built for exactly
  this and Fabric is not.

---

## Where each one is genuinely strongest

**Power BI report**
Governed distribution. Subscriptions and alerts. Excel export. Mobile layouts. Usage metrics. A
maintainer who doesn't write code. Certification and endorsement. It is the default for a reason, and
"can I do this in a report?" should stay the first question, not the last.

**Power Apps**
Governance you don't have to build: DLP, Conditional Access, admin-centre telemetry, sharing limits.
Transactional write-back with security roles. **Native mobile.** First-party support and an SLA.
And note — Power Apps has a genuine code path too: **Code Apps** (React/Vue in VS Code, `pac code
push`) and the mobile plugin (Expo/React Native). Anyone claiming "we write code and they don't"
hasn't looked.

**Fabric Apps**
Unlimited UI freedom — any npm library, WebGL, custom charts, an actual 3D scene. Direct access to
analytics-scale data with no copy and no extra per-user licence for the front end. And a repo: the
thing can be cloned, tested in CI, and handed to someone else.

---

## What you take on when you pick the app

Being clear about this is what makes the rest credible — and all five have a known answer.

- **Server-side logic lives outside the app.** There's no server-side function inside the app yet, so
  you add a Fabric User Data Function or an Azure Container App. Both work well; both are another
  moving part. (Detail: *Fabric Apps — three things to plan for*.)
- **The shell is served publicly.** Static hosting serves the bundle anonymously; the *data* stays
  Entra-gated, but the layout does not. If the layout itself is confidential, pick another surface.
- **The hostname is platform-owned.** No custom domain today, and it can change if the deployment
  binding is lost — keep `.deployments.json` and it stays put.
- **It's always on.** Hosting an app turns a schedulable capacity into a 24/7 one. Size the capacity
  to the app and this is cheap; leave it oversized and the uptime is what you're paying for, not the
  CU the app consumes.
- **You own the upgrade.** Preview surfaces move, and there's no SLA behind code you wrote yourself.

---

## Worked examples

Three things I built, and what each one is actually evidence *of*:

**A quota-calculation tool, rebuilt from a Power App.** React + Fluent UI on Fabric SQL with
write-back, 41 tests, and a reconciliation harness that measures its output against the original
rather than asserting they match. Evidence that the pattern is *achievable* — not that it was the
right call for every Power App.

**A university-enrolment story on public open data.** One Direct Lake model feeds an eight-page IBCS
report, a Fabric App with an animated race across six years, and a Data Agent. Evidence for the
opening claim: same measures, same model, three front ends, no choosing.

**A timetable planner.** Drag-and-drop with sub-second conflict detection and a CP-SAT solver
proposing repairs, writing back to Delta with versioned drafts and undo/redo — over a 3D campus that
carries a real constraint (travel time between sites). Evidence that some interactions have no
report-shaped equivalent at all.

---

## The summary I'd actually give

| | Power BI report | Power Apps | Fabric App |
|---|---|---|---|
| Maintainer | analyst | maker | dev team |
| UI ceiling | visuals available to you | templated → full code | unlimited |
| Data | the model | Dataverse + connectors | OneLake / Direct Lake, no copy |
| Write-back | no | transactional, with roles | build it yourself |
| Governance | mature | mature | Entra + workspace roles |
| Native mobile | yes | yes | web / PWA |
| Support | first-party | first-party, SLA | you own the code |

**Never say "Fabric is free."** Say: *no additional licence and no data duplication, **if** the data
is already in OneLake and you already have capacity* — and then be precise about what "already have
capacity" costs, because that is where the money actually is.

---

*Personal notes. Not official guidance, not an endorsement of one product over another, and not
affiliated with or endorsed by Microsoft.*
