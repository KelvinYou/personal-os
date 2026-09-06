# Nutrition Micronutrient Lookup — Technical Design

**Author:** Kelvin (drafted with agent assistance) **Status:** Approved — ready to implement **Last updated:** 2026-09-06
**Reviewers:** Kelvin

## 1. Context

`repos/notes` (public submodule) hosts a nutrition catalog — 44 foods in
`datasets/nutrition/foods/*.yaml` rendered as a searchable table on the notes site. Today the
dataset only carries macros (protein/carbs/fat/sugar/kcal, plus optional fibre/GI) — zero
vitamins or minerals exist anywhere in it, and the UI only supports "look up a food, read its
row." There is no path from "I'm low on iron" to "here's what to eat" without manually eyeballing
a wide table. This design adds micronutrient data (cited to USDA FoodData Central) and a second,
nutrient-first view alongside the existing food-first table.

**Out of scope:**
- Personalized RDA (age/sex/pregnancy-adjusted) — this uses one generic adult reference.
- Meal-level aggregation — the `meals/` dataset was already removed (2026-08-24, see
  `datasets/nutrition/README.md`); this design doesn't reintroduce it.
- Actual daily-intake tracking — this is a reference lookup, not a food log.

## 2. Scope

| # | Function | Change | Surface |
|---|---|---|---|
| 1 | Nutrition data schema (`schema.yaml`) | Modify | Data contract |
| 2 | RDA reference data | New | Data |
| 3 | Nutrition dataset validator | Modify | Build script |
| 4 | Nutrition docs generator | Modify | Build script |
| 5 | `FoodsExplorer` by-food table | Modify | Frontend |
| 6 | Nutrient Lookup view | New | Frontend |
| 7 | Micronutrient values for all 44 existing foods | New | Data content |
| 8 | `personal-os` `food_lookup` + `print_food` (`scripts/lib/nutrition/query.py`, `scripts/nutrition.py`) | Modify | Backend (Python, other repo) |

## 3. Current Architecture

```text
datasets/nutrition/foods/*.yaml + prices/*.yaml
        │
        ▼  scripts/generate-nutrition-docs.mjs
docs/health/nutrition/catalog/foods.mdx (generated)
        │
        ▼
src/components/FoodsExplorer  (food-first table: search / category filter / sort / column toggle)
```

**Current limitations**
- `schema.yaml`'s `food.optional_fields` has no micronutrient fields at all.
- `FoodsExplorer` only supports food→row navigation; there is no nutrient→foods path.
- `personal-os/scripts/lib/nutrition/query.py::food_lookup` also reads this same YAML directly
  (a second, real consumer outside this repo) — confirmed by reading the code, not assumed.

## 4. Proposed Architecture

```text
datasets/nutrition/foods/*.yaml        [MODIFIED — +17 optional micronutrient fields]
datasets/nutrition/rda_reference.yaml  [NEW]
        │
        ▼
scripts/validate-nutrition-data.mjs    [MODIFIED — validate new keys + RDA parity]
scripts/generate-nutrition-docs.mjs    [MODIFIED — emit micronutrients + rdaReference]
        │
        ▼
docs/health/nutrition/catalog/foods.mdx [MODIFIED — generated, page shape unchanged]
        │
        ▼
FoodsExplorer/index.tsx                [MODIFIED — tab control, grouped column dropdown]
FoodsExplorer/NutrientLookup.tsx       [NEW — nutrient-first ranked lookup]
```

> The design keeps the existing food-first table as the default view and adds a second,
> independent nutrient-first view fed by the same generated data — one data pipeline, one
> schema, no fork.

| Component | Change | Reason |
|---|---|---|
| `schema.yaml` | +17 optional micronutrient fields, +2 citation fields | Contract change other consumers read |
| `rda_reference.yaml` | New shared reference file | Powers %RDA display without per-food repetition |
| Validator | Key-membership + RDA-parity checks | Catch typos/missing RDA entries at build time, not render time |
| Generator | Pass through new fields + emit `rdaReference` | %RDA math stays build-time, same place `fmtPrice` already lives |
| `FoodsExplorer` | Tab control + grouped column dropdown | Existing default view must not regress |
| `NutrientLookup` (new) | Nutrient picker → ranked food list + %RDA badge | Answers "what should I eat for X" directly |

## 5. Data & Schema Changes

### New optional fields on `food` records

`iron_mg`, `calcium_mg`, `magnesium_mg`, `zinc_mg`, `potassium_mg`, `sodium_mg`, `iodine_ug`,
`vitamin_a_ug`, `vitamin_d_ug`, `vitamin_e_mg`, `vitamin_k_ug`, `vitamin_b1_mg`, `vitamin_b2_mg`,
`vitamin_b6_mg`, `vitamin_b12_ug`, `folate_ug`, `vitamin_c_mg`, `omega3_g` — plus
`micronutrient_source` (string, e.g. `"USDA FDC 173410"`) and `micronutrient_fdc_id`, kept
**separate** from the existing `source`/`last_verified` fields (those stay scoped to the
"personal shopping records, unverified" macro data — don't conflate an unverified macro source
with a cited USDA value on the same record).

**Unit convention (pin before population starts):** `vitamin_a_ug` = mcg RAE, `vitamin_d_ug` =
mcg — not IU for either. FDC exposes both; copying the IU column is a silent 40x error for
vitamin D that won't look obviously wrong anywhere downstream.

**Blank vs. zero:** a field left out means "not researched yet"; an explicit `0` means
"researched, confirmed negligible" (e.g. `vitamin_c_mg: 0` on chicken breast). Don't backfill
unresearched fields with `0`.

Example — before/after on an existing record:

```yaml
# before
- id: broccoli
  name: 花椰菜 (broccoli)
  basis: 100g_raw
  protein_g: 2.8
  carbs_g: 6.6
  fat_g: 0.4
  sugar_g: 1.7
  fibre_g: 2.6
  kcal: 34
  kcal_computed: true
  source: "personal shopping records (Malaysia), unverified"
  last_verified: "2026-08-31"

# after
- id: broccoli
  ...
  vitamin_c_mg: 89.2
  folate_ug: 63
  potassium_mg: 316
  iron_mg: 0.73
  micronutrient_source: "USDA FDC 170379"
  micronutrient_fdc_id: 170379
```

### New file — `datasets/nutrition/rda_reference.yaml`

```yaml
# Generic adult reference values (not personalized). Convention: generic US/EU DV —
# pairs with the USDA FDC source already used for the food data (one citation trail, not two).
iron_mg: 8
calcium_mg: 1000
vitamin_d_ug: 15
vitamin_c_mg: 90
# ... one entry per micronutrient key above
```

### Backward compatibility

**Additive-only, optional fields — no breaking change.** The one real external consumer,
`personal-os/scripts/lib/nutrition/query.py::food_lookup`, reads records through an explicit
field whitelist (`MACRO_FIELDS = [protein_g, carbs_g, fat_g, sugar_g, kcal]` plus
`glycemic_index`/`price`/`source`) and silently ignores unknown keys — so the new fields are
safe by default even before `food_lookup` itself is extended (§6 below extends it in the same
rollout, but the schema change alone can't break it either way).

## 6. Component Changes

**Validator (`scripts/validate-nutrition-data.mjs`)**
- Current: checks required fields, enum membership, id uniqueness, price↔food references.
- Proposed: also reject any micronutrient key not in the known 17, and require `rda_reference.yaml`
  to have an entry for every one of those 17 keys.
- Reason: typo/coverage guard at build time, same pattern as the existing `checkEnum`.

**Generator (`scripts/generate-nutrition-docs.mjs`)**
- Current: emits macro fields + GI + formatted price per row.
- Proposed: also emit the 17 micronutrient fields (when present) + `micronutrientSource`/`fdcId`,
  and a new `export const rdaReference = {...}`.
- Reason: %RDA is a display computation (row ÷ reference), same category as the existing
  `fmtPrice`/`priceNumber` helpers — stays build-time, doesn't touch `nutrition.py`'s territory.

**`FoodsExplorer/index.tsx`**
- Current: single food-first table, flat "Columns ▾" dropdown.
- Proposed: add a tab control (By food / By nutrient); group the column dropdown by section
  (Macros / Minerals / Vitamins) instead of one flat list, and keep the 6 current columns visible
  by default — new columns start hidden.
- Reason: a flat 24-item dropdown reproduces the exact "cluttered" UX this change is meant to fix.

**`FoodsExplorer/NutrientLookup.tsx` (new)**
- Nutrient picker (chips, grouped the same way as the column dropdown) → ranked list of foods
  with a value for that nutrient, sorted descending, each row showing the raw amount + a %RDA
  badge (≥20% "excellent source", ≥10% "good source", same nutrition-label language people
  already recognize). Reuses the existing search input to filter by food name.
- Empty state for nutrients the population pass (§7 of Scope) hasn't reached yet, instead of a
  blank list that reads as broken.

**`personal-os/scripts/lib/nutrition/query.py::food_lookup`** + **`scripts/nutrition.py::print_food`**
- Current: `food_lookup` returns `macros` (5 fields) + `glycemic_index`/`price`/`source`/
  `last_verified` — a fixed whitelist, micronutrients excluded by omission. `print_food` then
  explicitly formats each of those named fields (it does not dump the dict) — so the two need
  to change together, not `food_lookup` alone.
- Proposed: add a `micronutrients` dict to `food_lookup`'s return (same 17 keys, present only
  when populated on the underlying food) plus `micronutrient_source`/`micronutrient_fdc_id`,
  mirroring how `macros` is already built as `{f: food.get(f) for f in MACRO_FIELDS}`; then add
  a line to `print_food` that prints populated micronutrients (skip nutrients with no value,
  same "blank means unresearched" convention as the data itself — don't print "None").
- Reason: keeps the CLI and the web catalog in sync from the same rollout instead of a follow-up
  change nobody remembers to make.

## 7. Trade-offs

**Nutrient scope — curated ~10 vs. full common vitamin/mineral table**
Curated is less population work and ships faster. Full table is more complete but ~1.7x the
per-food research effort (17 vs. ~10 fields × 44 foods).
**Chosen: full table.** Decided with the user — a partial table would still leave common
deficiency-check nutrients (e.g. vitamin D, B12) unanswerable, defeating the point.

**Data source — keep "unverified personal record" vs. cite USDA FDC**
Keeping the existing unverified convention is zero extra work but produces numbers no more
trustworthy than a guess for values the user can't easily eyeball-sanity-check (unlike macros,
where a wildly wrong protein number is obvious). Citing USDA FDC is more work per record but
makes the data actually usable for a real deficiency decision.
**Chosen: USDA FDC, cited per record.** This also matches the dataset README's own "Known gaps"
note that per-row citation is owed to Phase 1.

**UX pattern — same table with more columns vs. separate page vs. new tab**
More columns in the existing table is zero new component code but scales badly — a 23-column
table is unreadable, and doesn't answer "what's rich in X" without manual sorting. A fully
separate page avoids touching the existing component but forks the "which foods exist" concept
across two independently-maintained UIs.
**Chosen: a second tab in the same component**, sharing the food list, categories, and search
input already built — no second data-shape to keep in sync.

## 8. Impact & Risks

**Impacted areas:** `repos/notes` Foods catalog page (public, currently live), the
generate/validate build scripts, and `personal-os`'s `nutrition.py food` CLI output
(`food_lookup` + `print_food`, both modified in this rollout).

| Risk | Mitigation |
|---|---|
| Default "By food" view gets cluttered by new columns | New columns hidden by default, grouped dropdown, existing 6-column default preserved |
| Vitamin A/D unit mixup (IU vs. mcg) | Convention pinned in schema comment before population starts, not left to whoever fills in each record |
| All-44-foods population pass still leaves some individual nutrients sparse (not every food is a source of every nutrient) | Explicit empty-state copy in Nutrient Lookup naming genuinely-low/no-data foods as such, not a silent blank list |
| Generated MDX inline JSON blob grows ~3x (44 records × 17 more fields) | Still small at this dataset size; revisit only if the catalog grows an order of magnitude |
| `nutrition.py food <id>` output gets noticeably longer per food (17 more possible lines) | Only print populated micronutrients, skip nulls — same convention as the data itself |

**Regression scope:** re-verify the existing "By food" default view (search/filter/sort/column
toggle) is pixel-for-pixel unchanged, and re-run the validator/generator against the full
existing 44-record dataset to confirm no current record fails the new checks.

## 9. Open Questions — resolved

1. ~~RDA reference convention~~ — **Generic US/EU DV**, pairs with the USDA FDC source already
   chosen for the food data (one citation trail, not two).
2. ~~Should `food_lookup` be extended~~ — **Yes, in this rollout.** `food_lookup` and
   `print_food` are both modified (§6, §8) so the CLI and web catalog ship in sync.
3. ~~Population order~~ — **All 44 foods now**, not a curated subset. This is the larger
   research pass (44 × 17 nutrient lookups against USDA FDC) but avoids a two-tier dataset where
   some foods are fully cited and others aren't yet.
