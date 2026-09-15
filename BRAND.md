# HiveRank brand guidelines

Notionhive product. Public landing for quick site checks. Staff dashboard for audits, snapshots, and bulk. Superadmin for access control.

---

## 1. What this brand is

**HiveRank** is Notionhive’s SEO command surface: anyone can run a full audit, SEO check, or speed test; signed-in operators manage history, snapshots, and bulk jobs; superadmins assign who can do what.

**Parent:** Notionhive  
**Product:** HiveRank  
**Locked casing:** `HiveRank` (capital H, capital R). Never Hiverank, Hive Rank, HIVERANK, NH SEO Tools, or HiveBrief (retired product name).

**Tagline:** Know where you stand. Climb with clarity.

**One-line:** Site health, rankings signal, and speed — reviewed inside the hive when it matters.

---

## 2. Architecture

Endorsed brand. Notionhive stays on leave-behind covers. HiveRank is the app and product line.

| Surface | Who | Job | Mode |
|---|---|---|---|
| Landing | Anyone | Analyze · SEO · Speed | Clear, calm marketing. One URL, one action. |
| Dashboard | Logged-in users | Audits, snapshots, bulk, history | Operate. Dense, scannable. |
| Access admin | Superadmin only | Users + permissions | Precise. No decoration. |
| Leave-behind deck | Prospect | Read a brief, book a call | 16:9 paper + Hive Blue rail. |

**Modules (product language)**

| Internal route | Product copy |
|---|---|
| `/` (landing) | HiveRank |
| Analyze / Full audit | Full Audit |
| SEO / Speed | SEO · Speed |
| Snapshot | Snapshot (staff leave-behind) |
| Bulk | Bulk Audit |
| Admin | Access |

---

## 3. Metaphor and mark

**Metaphor:** Standing on a ladder of clarity — rank as signal, not vanity. The hive is the parent; HiveRank owns **measurement + climb**.

**Mark direction (to design later):** Wordmark-first. Optional monogram **HR** — H as a vertical rail (progress), R as a rank step. Fill only. No bees, hexagons, honey, trophies, or magnifying glasses.

**Lockups**

- Horizontal: mark + HiveRank — default app header and landing.
- Mark only: favicon, slide footer.
- Endorsed: `HiveRank by Notionhive` — deck cover, email, marketing footer.

**Never:** outlined mark, glow, drop shadow on the mark, purple gradients, recolor except white-on-ink / ink-on-paper.

---

## 4. Color

Restrained system: cool paper neutrals + one primary (Notionhive blue) + status greens/ambers/reds. Same tokens in app and PPTX.

### Core

| Token | Hex | CSS var | Use |
|---|---|---|---|
| `hive` | `#1158E5` | `--color-hive` | Primary CTA, links, focus ring, deck rail, mark |
| `hive-dark` | `#0B3FA8` | `--color-hive-dark` | Hover / pressed primary |
| `hive-soft` | `#E8F0FE` | `--color-hive-soft` | Selected nav, chip wash, soft highlights |
| `ink` | `#0B1220` | `--color-ink` | Body text, wordmark, dark panels |
| `ink-soft` | `#1E293B` | `--color-ink-soft` | Secondary headings |
| `paper` | `#F4F6F9` | `--color-paper` | App / landing canvas |
| `white` | `#FFFFFF` | `--color-white` | Cards, inputs, slides |
| `line` | `#E2E8F0` | `--color-line` | Borders, table rules |
| `muted` | `#64748B` | `--color-muted` | Captions, meta only — never body copy |

### Status (always label + color)

| Token | Hex | Use |
|---|---|---|
| `pass` | `#059669` | Pass, healthy, CWV ok |
| `warn` | `#D97706` | Warn, thin data |
| `fail` | `#DC2626` | Fail, errors, blocking |

### Landing atmosphere (sparing)

| Token | Hex | Use |
|---|---|---|
| `sky-wash` | `#EEF4FF` → `#F4F6F9` | Soft vertical wash behind hero only |
| `ink-panel` | `#0B1220` | Footer or CTA band — not default page chrome |

**Do not:** purple/indigo themes, cream `#F4F1EA` + terracotta, neon glow, multi-layer shadows, black `#09090b` as the primary button (use `hive`).

**Contrast:** Body is `ink` on `paper` or `white`. Primary button label is white on `hive` (≥ 4.5:1). Status is never color-only — always Pass / Warn / Fail text.

---

## 5. Type

Two roles, one coherent system. No Inter, Roboto, Arial, or system UI stacks as the brand face.

| Role | Face | Weight | Notes |
|---|---|---|---|
| Wordmark, page titles, landing headlines | **Outfit** | 500–600 | Geometric, calm authority. Tracking `-0.02em` on wordmark |
| UI, body, forms, tables, deck body | **Plus Jakarta Sans** | 400 / 500 / 600 | Readable at density 6. Never 800 |
| Scores, timings, IDs | Plus Jakarta Sans | 500–600 | `font-variant-numeric: tabular-nums` |
| Code / raw payloads (rare) | **IBM Plex Mono** | 400 | Admin logs only |
| PPTX fallback | Calibri | — | Only if web fonts missing in PowerPoint |

**Why this pair:** Outfit carries the product name without shouting; Plus Jakarta Sans keeps dashboards and forms clear. Both are free (Google Fonts), load well on web, and sit cleanly next to Notionhive’s blue.

**Scale (app)**

| Step | Size | Use |
|---|---|---|
| caption | 12px | Meta, timestamps |
| body | 14–15px | Default copy |
| control | 14–16px | Inputs, buttons |
| section | 18–20px | Card / panel titles |
| page | 28–32px | Dashboard page titles |
| hero | 40–48px | Landing headline only |

**Deck type:** Prefer Plus Jakarta Sans (or Calibri fallback). Cover title can use Outfit if embedded; otherwise Plus Jakarta Sans Bold.

---

## 6. Shape and chrome

| Token | Value |
|---|---|
| Control radius | 8px (not pills) |
| Card radius | 12px |
| Deck corner | 4px |
| Border | 1px `line` — elevation is paper on paper |
| Focus | 2px `hive` ring, 2px offset |
| Shadow | None by default. Soft `0 8px 24px rgba(11,18,32,0.06)` only on landing hero CTA float if needed |

**Buttons**

- Primary: `hive` fill, white label — Analyze, Sign in, Approve, Save access.
- Ghost: `ink` on `white`, 1px `line`.
- Danger: `fail` outline or soft fill for revoke / delete.

**Icons:** Phosphor, stroke 1.5. Prefer rank / chart / gauge metaphors over bees.

**Motion:** 160–200ms opacity/color. Landing: one short fade-up on hero + subtle CTA hover. Honor `prefers-reduced-motion`.

---

## 7. Product surfaces

### Landing (public)

First viewport: **HiveRank** wordmark, one headline, one short line, URL field + Analyze (Full Audit / SEO / Speed as clear choices), Sign in. No stats strip, no card grid in the hero.

### Dashboard (logged-in)

Nav: Audits · Snapshots · Bulk · (Access if superadmin). History-first. Dense tables, filters, status chips.

### Access (superadmin)

Users list + permission toggles: Analyze · Snapshot · Bulk · Admin. Plain language: “Who can run what.”

### Deck

Keep left Hive Blue rail, 16:9.  
Cover: `HiveRank Snapshot for {domain}` (or module name).  
Filename: `HiveRank-{domain}.pptx`.  
Label Labs traffic/keywords **Estimated**.

---

## 8. Voice

Specialist, direct, no hype.

| Spot | Copy |
|---|---|
| App / landing title | HiveRank |
| Idle analyze | Paste a URL. Full audit, SEO, or speed. |
| Sign in | Staff and clients with access. |
| Snapshot | Pull a leave-behind. Someone reviews it before it goes out. |
| Thin data | Little keyword data. Technical and authority still ship. |
| Error | Could not pull this site. Check the URL and try again. |

**Banned:** unleash, seamless, next-gen, AI-powered, intelligence platform, auto-send, “guaranteed rankings.”

---

## 9. Implementation notes

```css
:root {
  --color-hive: #1158E5;
  --color-hive-dark: #0B3FA8;
  --color-hive-soft: #E8F0FE;
  --color-ink: #0B1220;
  --color-ink-soft: #1E293B;
  --color-paper: #F4F6F9;
  --color-white: #FFFFFF;
  --color-line: #E2E8F0;
  --color-muted: #64748B;
  --color-pass: #059669;
  --color-warn: #D97706;
  --color-fail: #DC2626;
  --font-display: "Outfit", system-ui, sans-serif;
  --font-body: "Plus Jakarta Sans", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
}
```

**Google Fonts import (app):**

```
Outfit:500,600
Plus Jakarta Sans:400,500,600
IBM Plex Mono:400
```

---

## 10. What’s next

1. Approve this guideline (colors + fonts).  
2. Mock landing → login → dashboard → Access admin in HTML.  
3. Wire tokens into the React app and retire “NH SEO Tools” / HiveBrief chrome.

**Retire:** Inter, zinc-as-brand, black primary buttons, HiveBrief product naming in UI.
