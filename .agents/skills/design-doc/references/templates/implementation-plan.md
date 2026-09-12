# Implementation Plan Template

For changes where the *how* is obvious and only the *order* needs writing down. One page. If you find yourself justifying a design choice, you've outgrown this tier — switch to Design-Lite.

---

# [Feature Name] — Implementation Plan

**Ticket:** … **Estimate:** … **Author:** …

## Goal

One or two sentences: what will be true when this is done. Written as an outcome the reviewer could verify, not as a task.

## Approach

Three to five sentences on how. Name the files, modules, or services involved — a plan that doesn't name where the code goes hasn't been thought through yet.

Include the one design choice you made, if any, and why. ("Extending `useWithdrawal` rather than adding a new hook, because the state is already there and a second hook would need to stay in sync.")

## Steps

Ordered, each independently reviewable, each with the file it touches. Mark steps that can happen in parallel.

1. Add `withdrawalType` to the request DTO — `api/dto/WithdrawalRequest.ts`
2. Thread it through the service call — `services/withdrawal.ts`
3. Add the form field and validation — `components/WithdrawalForm.tsx`
4. Update tests — `__tests__/withdrawal.spec.ts`

Keep this to the number of steps that actually reduce uncertainty. A plan that enumerates every keystroke is a to-do list, not a plan.

## Verification

How you'll know each part works: the test command, the manual check, the specific case that would catch a regression.

## Risks / Notes

Only the ones worth a reviewer's attention. Anything that could break existing behaviour, any assumption you're making, anything you'd want a second opinion on. Delete the section if there's genuinely nothing.

## Open Questions

Anything you need answered before or during implementation. Delete if none — but check honestly first, since "no open questions" on a real change usually means they haven't surfaced yet.
