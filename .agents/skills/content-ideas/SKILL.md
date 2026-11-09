---
name: content-ideas
description: >
  The owner's brainstorming partner for the XHS account: proposes and stress-tests post ideas,
  then files the chosen one into the Content Lab queue, where the autonomous pipeline produces it
  without further owner work. Use when the user wants to brainstorm content, asks "what should I
  post", "any post ideas", "help me think of a topic", shares a daily moment that might be a post,
  or says "queue this idea" / "go" on a discussed idea. Does not draw images or write the
  carousel; social-post owns production through the pipeline.
---

# Content Ideas

[Status: OK] The owner now has only two touchpoints: this conversation and the Review inbox. Everything in between runs autonomously (`docs/design/office-content-lab.md`, autonomy revision).

This skill is a thinking partner, not an idea vending machine. The owner keeps the question and the judgment (private `data/reference/personal-direction.md`). The agent brings evidence, counter-arguments and the reader's point of view.

## Read first

1. The `social-post` skill, §1 topic gate. Ideas are judged against the same five questions.
2. Private `data/posts/brand.md`: series, voice, audience.
3. Existing `data/posts/*/lab.yaml` files: stage, gate results, `pipeline.feedback` (what the owner rejected and why) and `measurements`. If three or more posts have 7-day results, say which gate questions actually predicted saves.
4. The last 30 days of private `data/daily/*.md`, searched for real friction with everyday systems: payments, transfers, tolls, tax, shopping, apps. A moment the owner actually lived through beats one the agent invents.

## The conversation

1. **Open with three candidates, not ten.** Each one gives: the reader's anxious moment in one line, gate score (Q1–Q5, with Q1 as a hard gate), where the evidence came from (a daily-log date, a WebSearch observation, or "agent hypothesis"), and the single riskiest assumption.
2. **Argue with the owner's own ideas.** For each, give the strongest reason it would fail, usually supply-driven topics or a happy path instead of a failure moment. Then say what would make it pass.
3. **Don't repeat what was rejected.** If `pipeline.feedback` or an archived post already rejected an angle, name it and offer a different one.
4. **Stop when the owner picks.** One idea per queue entry. Do not stack up a backlog nobody asked for; publishing more is not the goal.

## Filing an idea

Create `data/posts/<topic-slug>-YYYY-MM-DD/` (today's date, lowercase slug):

- `post.md`: `# <working title>`, then sections **Reader moment**, **Why now** (time hook or "none"), **Hypothesis** (what this post tests), **Changed variable**, **Evidence so far** (with sources and dates), **Must avoid** (the owner's constraints from the chat, verbatim).
- `lab.yaml`: `schema_version: 1`, `stage: idea`, plus `experiment.hypothesis` and `experiment.changed_variable`. Leave the gate and evidence to the pipeline's own check.

Run `make posts-check`. The idea now appears in Content Lab → Ideas.

**Queueing:** only when the owner says go ("go", "queue it", "做"), run:

```bash
printf '%s' '{"action":"approve_idea","post_id":"<id>","expected_revision":<revision or null>}' \
  | .venv/bin/python3 scripts/content_lab.py --apply --json
```

`revision` is the SHA-256 of the current `lab.yaml` bytes (`shasum -a 256`). Queueing starts the pipeline at once when `office.content_pipeline.enabled`. Otherwise it waits for `make content-run`. Tell the owner they will get a phone push when the package reaches review or fails.

## Never

- Queue an idea the owner didn't explicitly approve.
- Produce images, captions or carousels here.
- Claim search volume or trends you did not observe.
- Use employer or private-repository material in an idea without the owner's explicit clearance in this chat.
