# Scheduling a task re-runs its entire downstream subgraph

Tasks form a derivation chain (RELOAD source data -> compute -> EXPORT -> PUSH); downstream artifacts are derived from upstream outputs. When a Task is re-run its output can change, which makes everything downstream potentially stale.

We decided that `schedule(X)` re-runs X **and its entire downstream subgraph**, rather than the cheaper "only missing/failed downstream". In a clinical reporting context an internally inconsistent report (exports/pushes reflecting an older version of upstream data) is a data-integrity hazard that outweighs the cost of recomputation. The "only missing/failed" optimization is only safe for retrying a failed Task - and in that case downstream never ran, so it is already equivalent to re-running all downstream. It therefore buys nothing in the safe case and is dangerous in the unsafe one.

## Consequences

- Re-running an upstream Task can be expensive (heavy data processing across many downstream Tasks); this is accepted in exchange for guaranteed report consistency.
- If a narrower "retry this one Task" is ever needed, it must be a separate, explicitly named operation - not a weakening of `schedule`.
