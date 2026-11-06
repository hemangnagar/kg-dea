#!/usr/bin/env python3
"""Print what a hand-written narrative for each planned cable must contain.

Usage: .venv/bin/python -m scripts.narrative_worksheet [--max 50] [--ids DEA-000003-IIR-10 ...]

For each cable: agency, report date, source, marks per paragraph, the anchor
sentence each planted fact must appear as (canonical names; a unique alias may
replace a person's name after the first mention), the event context, planted
quantities and the corrected DocumentID. Writers put the result under
exemplars/narratives/<cable_id>.json as {"paragraphs": [{"number": 1, "text": "..."}, ...]}.
"""
import argparse
import json
from inteldoc.world import load_world
from inteldoc.store import connect
from inteldoc.models import Cable
from inteldoc.pipeline import VERBS, tables, canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=50)
    parser.add_argument('--ids', nargs='*')
    args = parser.parse_args()
    world = load_world()
    entities = {e['id']: e for e in world['entities']}
    counts = tables(world)[2]
    with connect() as db:
        rows = db.execute('SELECT id,record FROM cables ORDER BY rowid LIMIT ?', (args.max,)).fetchall()
    for row in rows:
        c = Cable.model_validate_json(row['record'])
        if args.ids and c.cable_id not in args.ids:
            continue
        print(f'=== {c.cable_id} | {c.agency} | report {c.report_date} | {c.classification} | source {c.source_id} ({c.reliability}) | {c.relevance} | place {c.place}')
        print(f'    subject: {c.subject}')
        if c.description:
            print(f'    context: {c.description}')
        if c.quantities:
            print(f'    planted quantities (only these numbers besides years): {c.quantities}')
        if c.corrects:
            print(f'    corrects: {c.corrects}')
        if c.dispute:
            print(f'    deliberate contradiction: {c.dispute}')
        people = {}
        for p in c.paragraphs:
            print(f'    [{p.number}] ({p.mark}) {len(p.facts)} facts')
            for f in p.facts:
                s, o = entities[f.subject], entities[f.object]
                window = f'from {f.date} until {f.until}' if f.until else f'on {f.date}'
                print(f'        {s["name"]} {VERBS[f.predicate]} {o["name"]} {window}.')
                for e in (s, o):
                    if e['kind'] == 'person':
                        people[e['name']] = [a for a in e['aliases'] if counts[canonical(a)] == 1]
        if people:
            print('    unique aliases usable after first mention: ' + '; '.join(f'{n}: {a}' for n, a in people.items()))
        print()


if __name__ == '__main__':
    main()
