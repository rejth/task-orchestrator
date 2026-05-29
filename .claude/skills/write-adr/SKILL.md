---
name: write-adr
description: Author a single Architectural Decision Record for a decision already made. Use when the user wants to record a decision retroactively (e.g. "write an ADR for X", "document this decision", "add ADR"), or when a hard-to-reverse trade-off surfaces during work and should be captured. For decisions still being grilled out, prefer `grill-with-docs` — it produces ADRs as a side effect of the grilling session.
---

# Write ADR

Author one ADR in `docs/adr/`. Format defined in [`grill-with-docs/ADR-FORMAT.md`](../grill-with-docs/ADR-FORMAT.md). This skill is the retro-document path; `grill-with-docs` is the during-decision path.

## Process

### 1. Decide if an ADR is warranted

ADR-FORMAT.md "When to offer an ADR" — all three must be true:

1. **Hard to reverse** — cost of changing later is meaningful
2. **Surprising without context** — future reader will wonder "why on earth?"
3. **Result of a real trade-off** — genuine alternatives existed

If any are false → skip. Don't ADR trivial choices.

If the user explicitly asks for an ADR, write it — but flag if criteria feel weak ("This is easy to reverse — sure you want an ADR?").

### 2. Read the existing set

```bash
ls docs/adr/ 2>/dev/null
```

- Note the highest existing number → next ADR = that + 1
- Read 1-2 existing ADRs to match house style (length, voice, optional sections)
- Check for related ADRs — if this decision supersedes/contradicts one, link it

If `docs/adr/` doesn't exist, create it lazily on the first ADR.

### 3. Gather context

Ask the user (one at a time, only if not already in conversation):

1. **Decision in one sentence.** What was decided?
2. **Why this over the obvious alternative?** The trade-off and the reasoning that tipped it.
3. **What constraint or context made the obvious option wrong?** Often the most useful part — invisible in code.

If the conversation already contains the answers, skip the ask and draft directly.

### 4. Draft

Use ADR-FORMAT.md template:

```md
# {Short title of the decision}

{1-3 sentences: what's the context, what did we decide, and why.}
```

Default = single paragraph. Add optional sections (`Status`, `Considered Options`, `Consequences`) only when they add genuine value per ADR-FORMAT.md.

**Title rules:**
- Active voice: "Use Postgres for the write model" not "Postgres usage decision"
- Concrete: "Drop Storybook in favor of Ladle" not "UI tooling change"

**Slug rules:**
- kebab-case
- Match title content
- Filename: `0001-use-postgres-for-write-model.md`

### 5. Confirm before writing

Show the draft. Let user edit. Then write to `docs/adr/NNNN-slug.md`.

### 6. Cross-link if applicable

If this ADR supersedes or contradicts an existing one:
- Add a one-line reference in the new ADR: "Supersedes ADR-0007."
- Edit the old ADR's `Status` to `superseded by ADR-NNNN` (only if it has status frontmatter; don't add status just for this — keep ADRs minimal).

### 7. Done

Confirm path written. Don't summarise the ADR back to the user — they just read it during step 5.

## What NOT to ADR

- Library choices that don't carry lock-in (npm dependencies you can swap in an hour)
- Code style / formatting decisions
- "Obvious" architectural choices with no real alternative
- Decisions that haven't actually been made yet — use `grill-with-docs` for those
- Anything that can be re-derived from the code with 5 minutes of reading

## Related skills

- `grill-with-docs` — produces ADRs during decision-making, not after
- `improve-codebase-architecture` — reads ADRs to inform refactors
- `tdd` — reads ADRs to avoid contradicting prior decisions in test design
