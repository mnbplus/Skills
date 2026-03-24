# Next Action

Prepare and sync a source-expansion release of `resource-hunter` with clear capability boundaries.

- Update release-facing docs so they match the current runtime:
  - source matrix
  - retrieval layers
  - indexed-discovery fallback behavior
  - Dalipan token-only limitation
- Clean sync boundaries before publishing:
  - exclude cache/build noise
  - keep only meaningful live-test evidence
  - avoid treating temporary probe scripts/pages as primary deliverables
- Keep the release note honest:
  - `AnimeTosho`, `DMHY`, `Torlock`, `DaliPan`, `search-index:bing`, and `search-index:brave` are now integrated
  - `DaliPan` currently provides structured clue records from anonymous search, not guaranteed final share URLs
  - `Bing` and `Brave` are best-effort indexed-discovery fallbacks
- After sync, continue the next implementation wave in this order:
  1. continue Dalipan detail/url completion only if anonymous/public evidence improves
  2. harden precision against same-title different-year trap cases and refresh release-gate evidence
  3. continue one-by-one probing for additional public no-API sources under the new admission checklist
