# Nutrition Source — Read Contract

Replaces the old `meal-library.md` (removed, see `docs/plan-public-knowledge-integration.md` §13.1).
The single owner of public food facts/prices is now `repos/notes` (public submodule);
this file only holds **query rules + private content that can't be extracted**.

> **Update 2026-08-24**: The structured meal templates (`datasets/nutrition/meals/`, and the
> `meal`/`search` subcommands of `nutrition.py`) have been removed — meal planning no longer
> assembles fixed food combinations. Instead, pick from "known food ids" + reference technique/
> pairing notes in the notes repo (marinades, overnight-oats combos, etc., see
> `repos/notes/docs/health/nutrition/`). `nutrition.py` now has only the `food` subcommand.

## Read priority (§10)

1. `data/user_profile.md` — personal goals, preferences, restrictions
2. `data/protocol/standard_week.md` — this week's baseline
3. `scripts/nutrition.py food <id>` — query only the specific food item needed
4. Only when the user asks for reasoning or specific technique, read the evidence/technique docs in
   `repos/notes/docs/health/nutrition/`

Meal planning **never reads the entire nutrition dataset** — only query the specific item needed.

## Query command

```sh
python3 scripts/nutrition.py food <food_id>
```

Example output:

```text
id: chicken_breast_raw
name: chicken breast (raw weight)
basis: 100g_raw
protein: 23g  carbs: 0g  fat: 3.6g  sugar: 0g
kcal: 124
price: ~RM1.5 / 100g
source_updated: 2026-08-19
```

**Known food ids** (confirm each one via `python3 scripts/nutrition.py food <id>` — never invent an id):
`egg`, `chicken_breast_raw`, `wholemeal_bread`, `brown_rice_cooked`, `white_rice_cooked`,
`potato`, `rolled_oats`, `greek_yogurt`, `whole_milk`, `cheese_slice`, `taiwan_sausage`,
`whey_protein_powder`, `ikan_kembung`, `tempeh`, `salmon_raw`, `dory_fillet_raw`,
`shrimp_peeled_raw`, `vegetables_mixed`, `almonds`, `walnuts`, `chia_seeds`,
`dark_chocolate_999`, `keto_almond_chocolate`, `black_sesame_powder`, `black_sesame_oil`,
`cocoa_powder_100`, `matcha_powder`, `frozen_blueberries`, `creatine_monohydrate`,
`magnesium_glycinate`.

**Technique/pairing references** (how-to docs, not structured data, human-readable):
`repos/notes/docs/health/nutrition/chicken-marinades.md` (3 chicken breast marinades),
`overnight-oats.md` (overnight oats combos + ratios), `supplements.md` (supplement evidence tiers).

## Explicit failure modes (no graceful fallback)

- `repos/notes` not checked out → `nutrition.py` hard-errors and prompts
  `git submodule update --init repos/notes` (notes is a public repo — anyone doing
  `clone --recursive` can get it; there's no permission-downgrade scenario like `data/`)
- Unknown food id, missing price
- Never silently fabricate nutrition values, never substitute a personal target for a public fact

---

The following content is **not extractable** (it all depends on `{{placeholder}}` or purely private
thresholds, see plan §9), kept as-is from the old `meal-library.md`:

## AM Training Day Meal Template (target `{{protein_target_g}}`g P / `{{kcal_training_day}}` kcal)

Protein target = `{{body_weight_kg}}` kg × `{{protein_per_kg}}` g/kg = `{{protein_target_g}}`g.

| Meal slot | Content | Protein | Carbs | Fat | kcal |
|------|------|---------|-------|-----|------|
| Pre-workout | Light, easily digestible carb/protein combo | per profile | per profile | per profile | per profile |
| Post-workout breakfast | High-protein breakfast + post-training carbs | per profile | per profile | per profile | per profile |
| Lunch | Protein source + vegetables + staple | per profile | per profile | per profile | per profile |
| Snack | Fills the day's remaining protein or carb/fat target | per profile | per profile | per profile | per profile |
| Dinner | Lean protein + vegetables; whether to add a staple is decided by profile | per profile | per profile | per profile | per profile |
| **Total** | Follows the phase target in `data/user_profile.md` §0 | `{{protein_target_g}}` | — | — | `{{kcal_training_day}}` |

Specific times, portions, restrictions, inventory, and top-up methods must be resolved from the private
profile/protocol; this file does not store personal version differences.
Choose food candidates from the "known food ids" above via `nutrition.py food <id>` one at a time — don't
hardcode example foods in this file.

## Rest Day Meal Template (target `{{protein_target_g}}`g P / `{{kcal_rest_day}}` kcal)

| Meal slot | Content | Protein | Carbs | Fat | kcal |
|------|------|---------|-------|-----|------|
| Breakfast | Protein-forward breakfast + moderate carbs/fat | per profile | per profile | per profile | per profile |
| Lunch | Protein source + vegetables + staple | per profile | per profile | per profile | per profile |
| Snack | Fills the day's remaining nutrition target | per profile | per profile | per profile | per profile |
| Dinner | Lean protein + vegetables; whether to add a staple is decided by profile | per profile | per profile | per profile | per profile |
| **Total** | Follows the phase target in `data/user_profile.md` §0 | `{{protein_target_g}}` | — | — | `{{kcal_rest_day}}` |

> Rest days still stay above the BMR floor (`{{bmr_floor_kcal}}` kcal). The gap to the `{{kcal_rest_day}}`
> target is about 300 kcal — same as training days: fill it with carbs/fat, not protein.

## Daily protein check

- **Current target: `{{protein_target_g}}`g/day (`{{protein_per_kg}}` g/kg × `{{body_weight_kg}}`kg)** —
  resolved from `data/user_profile.md` §0. Training and rest days are unified, no longer split.
- After meal planning, quickly sum protein and confirm it's close to `{{protein_target_g}}`g (±5-10g tolerance
  is fine, no need to hit it exactly)
- **Total > distribution**: prioritize hitting the daily total; 30-50g per meal is enough, no need to deliberately
  stack more
- **Whether pre-sleep casein is scheduled is decided by the private profile/protocol**; this file makes no
  assumption about the timing of the last meal

### Phase-switch mapping

**Do not maintain phase values in this file** — protein/calorie targets are all resolved from
`nutrition.<phase.current>` in `data/user_profile.md` §0. Switching phases only requires changing §0's
`phase.current`.

| Value needed | Key path |
|---|---|
| Current phase | `phase.current` |
| Protein target | `nutrition.<phase.current>.protein_g_target` |
| Training day kcal | `nutrition.<phase.current>.training_day_kcal` |
| Rest day kcal | `nutrition.<phase.current>.rest_day_kcal` |

## Dietary red lines

- Within the **2 hours before** a heavy compound-lift day (Leg Day / high-volume day), avoid large volumes of
  slow carbs and high-fat foods — this guards against digestive load triggering a vasovagal response. A light
  snack (banana, rice ball, etc. — fast carbs) is fine 1h before training
- Caffeine cutoff: 14:00 (past 16:00 counts as a serious violation, strongly linked to insomnia)
- **Calorie floor**: rest-day intake ≥ `{{bmr_floor_kcal}}`, specific value resolved from private profile
- **Fat floor**: ≥ `{{fat_floor_g}}`, specific value resolved from private profile
- **Weekly weight-loss rate**: follow the weight-change guardrails in the private profile; this file does not
  copy personal values

## Flexible eating rules

- **Reasonable compensation (cheat meal)**: when extremely fatigued on weekends, occasional indulgence
  (e.g. hotpot buffet) is allowed to protect the dopamine defense line
- **Binge-prevention substitution**: after extra snack intake, cut an equivalent amount of calories from the
  same or next meal. Dinner can reset to 200g Greek yogurt + almonds
- **Afternoon tea flexibility**: during a cut, ~200 kcal of carb budget can flex to an occasional afternoon
  tea (dessert/snacks); if unused it automatically becomes a larger deficit (bonus)

## Supplements (evidence-based only)

Evidence tiers documented in `repos/notes/docs/health/nutrition/supplements.md` (public evidence,
same citation set as Trommelen/Tagawa). Only dosage/timing is kept here — depends on the private
profile/protocol and can't be extracted:

| Supplement | Dose | Timing | Monthly cost |
|------|------|--------|--------|
| **Creatine Monohydrate** | 5g/day | with pre-workout shake | ~RM40 (see `nutrition.py food creatine_monohydrate`) |
| **Magnesium Glycinate** | per profile/protocol | pre-sleep slot from private protocol | market estimate (see `nutrition.py food magnesium_glycinate`) |
</content>
