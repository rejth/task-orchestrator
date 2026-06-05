# Polish and clean up the Task DAG console

## Parent

#33

## What to build

Finish the Task DAG console so it feels like a production operator surface rather than a prototype transplant. This pass should refine graph navigation, fit-view behavior, local-only node dragging, responsive layout, status styling, empty/error/loading presentation, and visual consistency with the existing app. It should also verify that generated prototype artifacts and non-project branding are not present in the production client source.

This slice should not introduce new domain behavior. It should make the completed graph console comfortable to use and ready for normal client checks.

## Acceptance criteria

- [ ] The graph supports normal navigation controls, including fit view or equivalent recovery from pan/zoom.
- [ ] Node dragging works as local-only UI state and does not persist positions.
- [ ] Refresh or reload can restore deterministic positions.
- [ ] The console remains usable on normal laptop-sized screens.
- [ ] The visual design uses restrained Task Orchestrator operator-console styling.
- [ ] Primary Task status display uses domain/API status vocabulary.
- [ ] Empty, loading, warning, and error states are visually clear in the graph console.
- [ ] No Manychat, Manyfest, branded generated fonts, branded token names, fake run controls, fake logs, fake durations, or prototype simulation remain in production client source.
- [ ] The current list console is fully replaced rather than duplicated beside the graph.
- [ ] Typecheck, client tests, and build verification pass for the Svelte Flow integration.

## Blocked by

- #34
- #35
- #36
- #37
- #38
