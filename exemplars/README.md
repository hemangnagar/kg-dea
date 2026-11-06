# Hand-written narrative exemplars

`narratives/<cable_id>.json` holds a hand-written narrative for one planned cable:

```json
{"cable_id": "FBI-000001-IIR-10", "paragraphs": [{"number": 1, "text": "..."}, {"number": 2, "text": "..."}]}
```

When `narratives_dir` is set in the corpus configuration (the default `config/corpus.yaml` points here), the generator uses the file instead of the offline template for that cable and runs it through the same deterministic checker as model output: every planted fact must appear as an anchor sentence in its assigned paragraph (`Subject verb Object on DATE.` or `from DATE until DATE.`, with a canonical name or a unique alias), no other dates, no numbers other than planted quantities and years, no capitalized multi-word names outside the world, 3 to 8 paragraphs and 250 to 900 words. `config/authored-50.yaml` is the strict form that fails any cable without a file.

Write the worksheet first:

```sh
.venv/bin/python -m scripts.narrative_worksheet --max 50
```

The 50 narratives here cover the first 50 planned cables of the default corpus (seed 42), written in this repository's sessions without any model API call. They are exemplars for a later model-rendering pass and the readable cables of the demo. No real document text is used.
