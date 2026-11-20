"""Plain-English briefs from graph facts.

The workspace page shows prose, not edges. `compose` turns the retrieved facts into sentences a reader needs no
training to follow, grouped into themed paragraphs, each carrying the facts (and so the citations) it was built from.
When a model is configured, `write` asks it to rewrite those sentences into a fluent analyst brief; the result is
accepted only if every paragraph cites real statement indexes and introduces no year that the statements do not
contain, otherwise the deterministic text is used. Either way nothing reaches the page that is not backed by a fact.
"""
import re
from pydantic import BaseModel, ConfigDict, Field

PRESENT = '2027'

THEMES = [
    ('leadership', 'Leadership and membership', ['leads', 'member_of', 'allied_with', 'split_from', 'elected_in', 'removed_in']),
    ('territory', 'Control of plazas and routes', ['controls']),
    ('finance', 'Companies, money and sanctions', ['owns', 'nominee_for', 'designated_in', 'paid_in']),
    ('events', 'Reported activity', ['participated_in', 'linked_to', 'occurred_at', 'transited', 'supported', 'involved_in', 'arrested_in', 'killed_in', 'extradited_in', 'released_in']),
    ('identifiers', 'Phones and accounts', ['uses']),
    ('communications', 'Partner call records', ['called']),
]

AGENCY_NAMES = {'DEA': 'DEA', 'FBI': 'FBI', 'HSI': 'HSI', 'CBP': 'CBP', 'DIA': 'DIA', 'TREASURY': 'Treasury', 'OSINT': 'open-source'}


def until_phrase(until):
    if not until:
        return ''
    if until >= PRESENT:
        return ' and, as far as the reporting shows, still does'
    return f' until {until}'


def event_phrase(entity):
    kind = (entity.get('event_type') or 'event').lower()
    article = 'an' if kind[0] in 'aeiou' else 'a'
    return f'{entity["name"]}, {article} {kind} in {entity.get("place", "an unreported place")},'


def describe(fact, names):
    s, o = names[fact['subject']], names[fact['object']]
    p, d, u = fact['predicate'], fact['date'], fact['until_date']
    S, O = s['name'], o['name']
    E = event_phrase(o) if o['kind'] == 'event' else O
    Es = event_phrase(s) if s['kind'] == 'event' else S
    company = f'{O}, a {o.get("sector", "")} company based in {o.get("place", "")},' if o['kind'] == 'company' else O
    corridor = f'the {O}' if o['kind'] == 'corridor' and not O.lower().startswith('the ') else O
    ident = 'phone' if 'TEL' in O else 'account' if 'ACCT' in O else 'identifier'
    table = {
        'leads': f'{S} led {O} from {d}{until_phrase(u)}.',
        'member_of': f'{S} was a member of {O} from {d}{until_phrase(u)}.',
        'allied_with': f'{S} was allied with {O} from {d}{until_phrase(u)}.',
        'split_from': f'{S} broke away from {O} on {d}.',
        'elected_in': f'{S} was chosen as leader at {E} on {d}.',
        'removed_in': f'{S} was removed from leadership at {E} on {d}.',
        'controls': f'{S} controlled {corridor} from {d}{until_phrase(u)}.',
        'owns': f'{S} owned {company} as of {d}.',
        'nominee_for': f'{S} was the registered owner of {company} as of {d}, a nominee fronting for the real owner.',
        'designated_in': f'{S} was designated for sanctions through {E} on {d}.',
        'paid_in': f'{S} was party to a payment in {E} on {d}.',
        'participated_in': f'{S} took part in {E} on {d}.',
        'linked_to': f'{S} was linked to {E} on {d}.',
        'occurred_at': f'{Es} took place at {O} on {d}.',
        'transited': f'{Es} moved through {corridor} on {d}.',
        'supported': f'{S} supported {E} on {d}.',
        'involved_in': f'{S} was involved in {E} on {d}.',
        'arrested_in': f'{S} was arrested during {E} on {d}.',
        'killed_in': f'{S} was killed in {E} on {d}.',
        'extradited_in': f'{S} was extradited in {E} on {d}.',
        'released_in': f'{S} was released in {E} on {d}.',
        'uses': f'{S} used the {ident} {O} on {d}.',
        'called': f'{S} called {O} on {d}.',
    }
    return table.get(p, f'{S} {p.replace("_", " ")} {O} on {d}.')


def statements(facts, names):
    """One plain-English sentence per fact, in the facts' order, plus the theme each belongs to."""
    theme_of = {p: key for key, _, preds in THEMES for p in preds}
    out = []
    for i, f in enumerate(facts):
        out.append({'index': i, 'theme': theme_of.get(f['predicate'], 'events'), 'text': describe(f, names), 'fact': f})
    return out


def merge_calls(items, names):
    """'A called B on d' repeated becomes one sentence with a count and a date span."""
    groups = {}
    for it in items:
        f = it['fact']
        groups.setdefault((f['subject'], f['object']), []).append(it)
    merged = []
    for (s, o), group in groups.items():
        dates = sorted(x['fact']['date'] for x in group)
        text = (f"{names[s]['name']} called {names[o]['name']} on {dates[0]}." if len(dates) == 1 else
                f"{names[s]['name']} called {names[o]['name']} {len(dates)} times between {dates[0]} and {dates[-1]}.")
        merged.append({'text': text, 'indexes': [x['index'] for x in group]})
    return merged


def compose(question, facts, names, persona, cables_cited, agencies, calls_cited):
    """Deterministic brief: an overview paragraph, one paragraph per theme present, a closing note on access."""
    items = statements(facts, names)
    subjects = sorted({names[f['subject']]['name'] for f in facts} | {names[f['object']]['name'] for f in facts})
    agency_text = ', '.join(AGENCY_NAMES.get(a, a) for a in sorted(agencies)) or 'no agency'
    paragraphs_cited = sum(f['count'] for f in facts if not f['predicate'] == 'called')
    sources = []
    if paragraphs_cited:
        sources.append(f'{paragraphs_cited} paragraph{"s" if paragraphs_cited != 1 else ""} in {cables_cited} cable{"s" if cables_cited != 1 else ""} reported by {agency_text}')
    if calls_cited:
        sources.append(f'{calls_cited} partner call record{"s" if calls_cited != 1 else ""} from the FBI')
    overview = (f'The accessible reporting supports {len(facts)} relationship{"s" if len(facts) != 1 else ""} relevant to this question, '
                f'drawn from {" and ".join(sources) if sources else "no source"}.')
    paragraphs = [{'text': overview, 'facts': list(range(len(facts)))}]
    described_events = set()
    for key, title, _ in THEMES:
        group = [it for it in items if it['theme'] == key]
        if not group:
            continue
        if key == 'communications':
            merged = merge_calls(group, names)
            paragraphs.append({'title': title, 'text': ' '.join(m['text'] for m in merged) + ' These come from partner call records, where each phone label is resolved to the person who held it on the day of the call.',
                               'facts': [i for m in merged for i in m['indexes']]})
            continue
        sentences, indexes = [], []
        seen = set()
        for it in group:
            f = it['fact']
            # Two cables that disagree on a date are both reported, with the disagreement said out loud.
            dup = (f['subject'], f['predicate'], f['object'])
            if dup in seen:
                sentences.append(f'Another cable gives the date as {f["date"]} for the same relationship, so the reporting disagrees on when it happened.')
                indexes.append(it['index'])
                continue
            seen.add(dup)
            sentences.append(it['text'])
            indexes.append(it['index'])
            for side in ('subject', 'object'):
                e = names[f[side]]
                if e['kind'] == 'event' and e['id'] not in described_events and e.get('description'):
                    described_events.add(e['id'])
                    sentences.append(f'Reporting describes that {e.get("event_type", "event").lower()} this way: {e["description"].strip()}')
        paragraphs.append({'title': title, 'text': ' '.join(sentences), 'facts': indexes})
    if persona == 'unclassified':
        paragraphs.append({'text': 'Only Unclassified paragraphs were consulted for this brief. Secret reporting and partner call records, which carry law-enforcement-sensitive handling, were not available to this user and may say more.', 'facts': []})
    return paragraphs


class BriefParagraph(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=4000)
    statements: list[int] = Field(min_length=1, max_length=60)


class Brief(BaseModel):
    model_config = ConfigDict(extra='forbid')
    paragraphs: list[BriefParagraph] = Field(min_length=1, max_length=8)


def write(question, facts, names, persona, provider, settings):
    """Model-written brief from the deterministic statements. Returns paragraphs or raises ValueError when ungrounded."""
    from .llm import request
    items = statements(facts, names)
    notes = {}
    for f in facts:
        for side in ('subject', 'object'):
            e = names[f[side]]
            if e['id'] not in notes:
                notes[e['id']] = {'name': e['name'], 'kind': e['kind'], 'place': e.get('place'),
                                  **({'aliases': e['aliases']} if e.get('aliases') else {}),
                                  **({'description': e['description']} if e['kind'] == 'event' and e.get('description') else {}),
                                  **({'sector': e['sector']} if e['kind'] == 'company' and e.get('sector') else {})}
    result = request(provider,
                     'Write an analyst brief in plain English that answers the question for a reader who knows nothing about '
                     'the system or its vocabulary. Use ONLY the numbered statements as facts; the entity notes give background '
                     'wording (what kind of thing each name is, what an event was). Do not add, infer or soften any fact, and '
                     'keep every name, date and number exactly as given, dates in the YYYY-MM-DD form. Write two to five short paragraphs: first a direct answer '
                     'to the question, then the detail grouped by topic, in full sentences, no bullet points, no headings, no '
                     'mention of graphs, databases, predicates or this instruction. Only if two statements give different dates for the '
                     'same relationship, say that the reporting disagrees; otherwise do not comment on dates. For each paragraph list '
                     'the indexes of the statements it used; every statement must be used at least once.',
                     {'question': question, 'persona': 'Secret // NOFORN' if persona == 'secret' else 'Unclassified // FOUO (Secret reporting was not available)',
                      'statements': [{'index': it['index'], 'text': it['text']} for it in items], 'entity_notes': list(notes.values())},
                     Brief, settings.get('brief_max_output_tokens', 1800))
    allowed_years = set(re.findall(r'\b(?:20[0-2]\d)\b', question + ' ' + ' '.join(it['text'] for it in items) + ' ' + ' '.join(str(n.get('description', '')) for n in notes.values())))
    paragraphs, used = [], set()
    for p in result.paragraphs:
        indexes = sorted({i for i in p.statements if 0 <= i < len(items)})
        if not indexes:
            raise ValueError('Model paragraph cites no real statement')
        if set(re.findall(r'\b(?:20[0-2]\d)\b', p.text)) - allowed_years:
            raise ValueError('Model paragraph introduces a year the statements do not contain')
        paragraphs.append({'text': p.text.strip(), 'facts': indexes})
        used |= set(indexes)
    if len(used) < max(1, int(0.6 * len(items))):
        raise ValueError('Model brief dropped too many statements')
    if persona == 'unclassified':
        paragraphs.append({'text': 'Only Unclassified paragraphs were consulted for this brief. Secret reporting and partner call records were not available to this user and may say more.', 'facts': []})
    return paragraphs
