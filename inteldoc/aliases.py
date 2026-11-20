"""Analyst-added aliases.

An analyst can attach a new name to an entity from the interface. Aliases live in their own table, so the published
world is never rewritten, and they join the entity's alias list wherever the graph resolves names: question matching,
the explorer's center box, the entity typeahead and disambiguation. Adding a name that another entity already carries
makes it a shared alias, so questions using it ask the analyst to choose, exactly as the published shared nicknames do.
"""
import re
from .store import connect

MAX_LENGTH = 60


def normalise(alias):
    alias = re.sub(r'\s+', ' ', (alias or '').strip())
    if not 1 <= len(alias) <= MAX_LENGTH:
        raise ValueError(f'An alias is 1 to {MAX_LENGTH} characters')
    if re.search(r'[<>{}\[\]\\|^~`]', alias):
        raise ValueError('An alias is a name: letters, digits, spaces and ordinary punctuation')
    return alias


def listing():
    with connect() as db:
        rows = db.execute('SELECT entity,alias,added_by,added_at FROM alias_overrides ORDER BY entity,alias').fetchall()
    return [dict(r) for r in rows]


def by_entity():
    out = {}
    for row in listing():
        out.setdefault(row['entity'], []).append(row['alias'])
    return out


def add(entity, alias, added_by='analyst'):
    alias = normalise(alias)
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO alias_overrides VALUES(?,?,?,datetime('now'))", (entity, alias, added_by))
    return alias


def remove(entity, alias):
    with connect() as db:
        db.execute('DELETE FROM alias_overrides WHERE entity=? AND alias=?', (entity, alias))


def clear():
    with connect() as db:
        db.execute('DELETE FROM alias_overrides')


def version():
    with connect() as db:
        n, mx = db.execute('SELECT count(*), COALESCE(max(rowid),0) FROM alias_overrides').fetchone()
    return f'{n}:{mx}'
