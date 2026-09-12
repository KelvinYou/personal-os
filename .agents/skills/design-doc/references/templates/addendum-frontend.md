# Frontend Addendum

Attach to a Design-Lite or Design-Full doc when the frontend change is deep enough that "modify the withdrawal form" doesn't tell a reviewer anything. Skip it entirely for a field addition.

Include only the subsections with real content.

---

## Frontend Design

### Component & state changes

Which components are new, modified, or removed, and where they sit in the tree. For each, what state it owns and where that state lives now (local, context, store, server cache).

The question a reviewer is actually asking: **does this add a second source of truth?** Answer it directly.

### Data flow

How data gets from the API to the screen and back. Name the fetching layer (React Query key, store slice, loader). Note what's cached, when it invalidates, and what a stale read would look like to the user.

### Routing & navigation

New routes, changed URLs, deep links, guards. Whether an existing URL changes meaning — that breaks bookmarks and any external link, so call it out.

### UI states

Every meaningful state, not just the happy one: loading, empty, partial, error, offline, permission-denied, in-flight/disabled. A design that hasn't specified its error state hasn't specified its error handling.

| State | Trigger | UI |
|---|---|---|
| Validating | Pre-submit check in flight | Submit disabled, inline spinner |
| Over limit | `LIMIT_EXCEEDED` from validate | Inline error with the applicable limit |

### Validation

What's validated client-side and what's authoritative server-side. Client validation is UX; server validation is the rule. Say which is which so nobody mistakes a form check for enforcement.

### Cross-client consistency

If Web and Mobile both implement this, what keeps them consistent — a shared endpoint, shared config, or nothing (in which case, name the divergence risk).

### Performance

Only when the change plausibly affects it: bundle size of a new dependency, added render or request on a hot path, list virtualization, image weight.

### Accessibility & i18n

Keyboard and screen-reader handling for new interactive elements; focus management for new modals or flows. New user-facing strings and whether they need translation before release. Formats that vary by locale — currency, dates, number separators.

### Backward compatibility

For mobile or long-lived web sessions: what happens when an old client hits the new API, and when a new client hits an old API during rollout.
