# Feature / Bug-Fix SOP

Day-to-day dev loop: ticket intake to deploy. Splits into a simple path and a
complex path right after Design — complexity decides how much structure the
implementation phase needs, not whether design/test/review happen at all.

```mermaid
flowchart TD
    A["Ticket<br/>Jira / Meegle / GitHub Issue"] --> B["Design<br/>design-doc skill:<br/>plan / lite-spec / ADR"]
    B --> C{"Complexity?"}

    C -- "Simple" --> D1["Implement<br/>single pass, code + unit tests"]
    D1 --> D2["AI-automated Playwright test"]
    D2 --> D2A{"Pass?"}
    D2A -- "No" --> D1
    D2A -- "Yes" --> D3["Review<br/>code-review skill / PR"]
    D3 --> D3A{"Approved?"}
    D3A -- "No" --> D1
    D3A -- "Yes" --> Z

    C -- "Complex" --> E1["Plan splits into subtasks<br/>written into the design doc"]

    subgraph LOOP["Per-subtask loop (TDD)"]
        E1 --> E2["Pick next subtask"]
        E2 --> E2T["Write/update this subtask's<br/>test first (red), tdd skill"]
        E2T --> E3["AI implements against<br/>the failing test"]
        E3 --> E4{"Diff matches this<br/>subtask's scope in the plan?"}
        E4 -- "No, drifted" --> E3
        E4 -- "Yes" --> E5["Fast unit/integration test<br/>for this subtask (green?)"]
        E5 --> E5A{"Pass?"}
        E5A -- "No" --> E3
        E5A -- "Yes" --> E6{"More subtasks<br/>left in the plan?"}
        E6 -- "Yes" --> E2
    end

    E6 -- "No" --> E7["Full-flow Playwright test<br/>across all integrated subtasks"]
    E7 --> E7A{"Pass?"}
    E7A -- "No" --> E2
    E7A -- "Yes" --> E8["Review<br/>code-review skill / PR"]
    E8 --> E8A{"Approved?"}
    E8A -- "No, plan itself is wrong" --> B
    E8A -- "No, execution only" --> E2
    E8A -- "Yes" --> Z

    Z["Merge<br/>git-commit skill"] --> ZZ["Deploy"]
    ZZ --> ZZZ["Monitor / verify in prod"]
    ZZZ -.->|"next ticket"| A

    classDef intake fill:#e8f0fe,stroke:#4285f4
    classDef simple fill:#fff8e1,stroke:#f9a825
    classDef complex fill:#f3e5f5,stroke:#8e24aa
    classDef gate fill:#fce4ec,stroke:#d81b60
    classDef ship fill:#e0f2f1,stroke:#00897b

    class A,B intake
    class D1,D2,D3 simple
    class E1,E2,E2T,E3,E7 complex
    class D2A,D3A,E4,E5,E5A,E6,E7A,E8,E8A gate
    class Z,ZZ,ZZZ ship
```

## Reading it

- **Complexity is decided once, right after Design** — not per-subtask. If the
  plan turns out to need splitting mid-flight, that's a sign Design
  under-scoped it; treat it as a plan revision (`E8A` "plan itself is wrong"
  loops back to **B**, not around the loop).
- **Simple path**: one implementation pass, one test gate, one review gate.
  This is the default — don't route a change through the subtask loop unless
  it actually needs it.
- **Complex path — the per-subtask loop is TDD, not implement-then-check**:
  write/update that subtask's test first (`E2T`, `tdd` skill) so the AI
  iterates against a concrete red→green signal, not just "looks right."
  Check the diff against the plan (`E4`) before running the test, and only
  pull the next subtask once the current one is green. This catches scope
  drift per-subtask instead of discovering it after everything's implemented.
- **Two test gates, different speeds**: `E5` is a fast unit/integration test
  run per subtask — deliberately not Playwright, since E2E is too slow to run
  inside a tight per-subtask loop. `E7` is the one full Playwright E2E pass,
  run once after all subtasks are integrated — a subtask can pass alone and
  still break when combined with the others, so this gate exists even though
  each subtask already passed `E5`.
- **Review failure branches by cause** (`E8A`): "execution didn't match an
  otherwise-correct plan" loops back into the subtask loop; "the plan itself
  was wrong" goes all the way back to Design. Don't reflexively send every
  review rejection back to Design.
