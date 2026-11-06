# Claude Haiku full-corpus status

Completed: 2026-11-06.

**5,000 validated documents, zero failed**, from the hand-authored world. 4,949 were rendered and extracted by Claude Haiku 5.5; 51 are hand-written (the 50 pilot exemplars plus one cable the model could not render without shortening an asset name).

Accounted spend including the pilot, probes and all retries: **$12.17**, below the $40 cap. Wall clock about 2.5 hours at eight workers.

Scorecard: planted recall 0.999, world recall 0.971, precision 1.0 excluding 178 planted contradictions, 68 correction cables, 173 rejected model claims.

The first pass was interrupted once by a transient provider error and resumed from checkpoints. Five automatic retry passes cleared most failures; the dominant cause was the model naming a real region or shortening an entity name, which the instruction now forbids. Twenty-six cables whose cached drafts contained such a phrase were regenerated from fresh drafts.

Browse [the results and run report](../artifacts/haiku-5000/README.md) or [download the archive](../artifacts/haiku-5000-results.zip).

The earlier OpenAI pilot under `artifacts/pilot-50/` ran against the previous template world and is superseded by this corpus.
