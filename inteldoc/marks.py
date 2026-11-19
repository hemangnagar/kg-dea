"""Runtime re-marking of cable paragraphs.

A demo control: an analyst with the Secret persona can change a paragraph's portion mark between S//NF and U//FOUO.
Overrides live in their own table and are applied when evidence and cables are read, so the corpus itself is never
rewritten and "Reset" restores the published marks. Partner call records (FBI-CDR rows) carry LES handling and are
not re-markable.
"""
from .store import connect

MARKS = {'S': ('S', 'NF'), 'U': ('U', 'FOUO')}


def overrides():
    """{(cable, paragraph): (classification, controls)} for every active override."""
    with connect() as db:
        rows = db.execute('SELECT cable,paragraph,classification,controls FROM mark_overrides').fetchall()
    return {(r['cable'], r['paragraph']): (r['classification'], r['controls']) for r in rows}


def listing():
    with connect() as db:
        rows = db.execute('SELECT cable,paragraph,classification,controls,original_classification,original_controls FROM mark_overrides ORDER BY cable,paragraph').fetchall()
    return [dict(r) for r in rows]


def mark_text(classification, controls):
    return classification + ('//' + controls.replace(',', '//') if controls else '')


def apply(rows):
    """Return evidence rows with overridden marks. Rows are dicts; untouched rows are returned as-is."""
    current = overrides()
    if not current:
        return rows
    out = []
    for r in rows:
        key = (r['cable'], r['paragraph'])
        if key in current:
            r = {**r, 'classification': current[key][0], 'controls': current[key][1]}
        out.append(r)
    return out


def set_mark(cable, paragraph, classification):
    """Override one paragraph's mark. Returns the effective (classification, controls). Raises KeyError if unknown."""
    if classification not in MARKS:
        raise ValueError('classification must be S or U')
    new_class, new_controls = MARKS[classification]
    with connect() as db:
        row = db.execute('SELECT classification,controls FROM evidence WHERE cable=? AND paragraph=? AND cable NOT LIKE ? LIMIT 1',
                         (cable, paragraph, 'FBI-CDR-%')).fetchone()
        if row is None:
            raise KeyError('No such paragraph in the evidence')
        existing = db.execute('SELECT original_classification,original_controls FROM mark_overrides WHERE cable=? AND paragraph=?', (cable, paragraph)).fetchone()
        original = (existing['original_classification'], existing['original_controls']) if existing else (row['classification'], row['controls'])
        if (new_class, new_controls) == original:
            db.execute('DELETE FROM mark_overrides WHERE cable=? AND paragraph=?', (cable, paragraph))
        else:
            db.execute('INSERT OR REPLACE INTO mark_overrides VALUES(?,?,?,?,?,?)', (cable, paragraph, new_class, new_controls, original[0], original[1]))
    return new_class, new_controls


def clear(cable=None, paragraph=None):
    with connect() as db:
        if cable is None:
            db.execute('DELETE FROM mark_overrides')
        else:
            db.execute('DELETE FROM mark_overrides WHERE cable=? AND paragraph=?', (cable, paragraph))


def version():
    """Changes whenever the override set changes; used to key caches."""
    with connect() as db:
        n, mx = db.execute('SELECT count(*), COALESCE(max(rowid),0) FROM mark_overrides').fetchone()
    return f'{n}:{mx}'
