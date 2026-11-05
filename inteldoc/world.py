"""World expansion: hand-authored seed (schema 3) -> expanded world + graph truth.

Everything generated here is derived from the seed by code. The generated
routine events are sampled from the world's own structure (who controls which
corridor when, who is a member of what, who owns which company), never at
random from flat lists, so every generated fact is consistent with the bible.
"""
import json
import os
import random
from datetime import date, timedelta
from pathlib import Path
import yaml
from .models import Fact

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = '2027-01-01'
CORPUS_START, CORPUS_END = date(2010, 1, 1), date(2026, 10, 31)

ROLE_PREDICATE = {'reported-participant': 'participated_in', 'organization': 'linked_to', 'counterparty': 'linked_to',
                  'departing-leader': 'participated_in', 'arrested': 'arrested_in', 'victim': 'killed_in',
                  'extradited': 'extradited_in', 'released': 'released_in', 'incoming-official': 'elected_in',
                  'outgoing-official': 'removed_in', 'payee': 'paid_in', 'designated': 'designated_in',
                  'company': 'supported', 'asset': 'involved_in'}

FIRST_NAMES = ['Adrián', 'Beatriz', 'Cipriano', 'Dolores', 'Efraín', 'Fabiola', 'Gerardo', 'Hilda', 'Isidro', 'Jovita',
               'Leocadio', 'Magdalena', 'Nicanor', 'Ofelia', 'Pascual', 'Rosaura', 'Severo', 'Teresa', 'Ulises', 'Vicenta',
               'Wenceslao', 'Ximena', 'Zacarías', 'Amalia', 'Bonifacio', 'Clotilde', 'Demetrio', 'Eulalia', 'Froylán', 'Genoveva',
               'Hipólito', 'Inés', 'Justino', 'Leticia', 'Macario', 'Natalia']
SURNAMES = ['Abundis', 'Balderas', 'Carbajal', 'Delgadillo', 'Escandón', 'Fregoso', 'Gamboa', 'Hinojosa', 'Izaguirre', 'Jaramillo',
            'Lomelí', 'Magallanes', 'Noriega', 'Orozco', 'Pantoja', 'Quezada', 'Rentería', 'Sandate', 'Tiscareño', 'Ugalde',
            'Verduzco', 'Yáñez', 'Zúñiga', 'Alanís', 'Bocanegra', 'Cedillo', 'Dorantes', 'Esquivel', 'Frausto', 'Garibay',
            'Huerta', 'Iniesta', 'Jáuregui', 'Lozano', 'Mascareñas', 'Nájera', 'Ornelas', 'Padilla', 'Quintero', 'Rangel',
            'Salcedo', 'Tovar', 'Urbina', 'Valenzuela', 'Zamudio', 'Arreola', 'Bermúdez', 'Covarrubias']
NICKNAMES = ['El Tecolote', 'La Tortuga', 'El Candado', 'El Serrucho', 'La Luciérnaga', 'El Barómetro', 'El Cerillo', 'La Veleta',
             'El Tornillo', 'El Pizarrón', 'El Sapo Verde', 'La Lechuza', 'El Farolito', 'El Cometa Rojo', 'El Cascabel', 'La Brisa',
             'El Chilacayote', 'El Tanque', 'El Pelícano', 'La Ardilla', 'El Mapache', 'El Zorrillo', 'El Pinche Lápiz', 'La Abeja',
             'El Jarocho Chico', 'El Molcajete', 'El Tlacuache', 'La Garrapata', 'El Chapulín', 'El Cucharón', 'El Coyote Flaco',
             'El Tordo', 'La Jicotera', 'El Pirul', 'El Soldadito', 'La Grulla', 'El Marrano', 'El Cenzontle', 'El Huarache',
             'La Luna Chica', 'El Chamuco', 'El Mezquite', 'El Caracol', 'La Urraca', 'El Chivo Negro', 'El Pato', 'El Nopal',
             'La Tarántula', 'El Zanate', 'El Perico', 'El Mosco', 'El Guajolote', 'La Quelite', 'El Tamal', 'El Ciempiés',
             'El Venado', 'La Polilla', 'El Jilguero', 'El Mochuelo', 'El Carrizo', 'El Chile Seco', 'La Pantera Gris',
             'El Gorrión', 'El Tejón', 'El Dos Tres', 'La Hormiga Roja', 'El Gavilán', 'El Pelón Chico', 'El Metate',
             'La Libélula', 'El Chocolate', 'El Armadillo', 'El Borrego', 'La Calandria', 'El Cien', 'El Tintero', 'El Papalote',
             'El Guacamayo', 'La Paloma Negra', 'El Alacate', 'El Remolino', 'El Trique', 'La Ventisca', 'El Cuervo Blanco',
             'El Sereno', 'El Escarabajo', 'La Garza Chica', 'El Chaparro Azul', 'El Picudo', 'El Tabique', 'El Colibrí',
             'La Granada', 'El Topo', 'El Grillo', 'El Pulpo', 'La Marmota', 'El Chacal', 'El Ocelote', 'El Cóndor', 'El Rebozo']
COMPANY_PREFIX = {'trucking': ['Transportes', 'Fletes', 'Autotransportes', 'Logística'],
                  'produce-export': ['Exportadora', 'Agrícola', 'Empacadora', 'Frutas'],
                  'currency-exchange': ['Cambios', 'Divisas', 'Casa de Cambio'],
                  'used-cars': ['Autos', 'Seminuevos', 'Camiones'],
                  'mining': ['Minera', 'Agregados'],
                  'hospitality': ['Hotel', 'Posada', 'Hospedaje', 'Restaurante']}
COMPANY_SUFFIX = ['del Valle Hondo', 'Cerro Azul', 'Río Seco', 'La Ceiba Alta', 'Monte Claro', 'Playa Larga', 'del Norte Frío',
                  'Sierra Pálida', 'Luz de Agave', 'Piedra Lisa', 'Bahía Quieta', 'Nube Roja', 'del Cedro Blanco', 'Vientos del Sur',
                  'Pico Lunar', 'La Garita Vieja', 'Dunas Altas', 'Arroyo Pardo', 'Cumbre Clara', 'Olas Grises', 'Tierra Dorada',
                  'Nogal Viejo', 'Sol Poniente', 'Cuatro Vientos', 'Punta Serena', 'Barranca Honda', 'Colina Fría', 'Valle Pardo',
                  'Mesa Larga', 'Rayo Verde', 'Marea Lenta', 'Estero Claro', 'Alto Cedro', 'Ribera Quieta', 'Sauce Negro',
                  'Lomas del Faro', 'Puerto Lento', 'Encino Solo', 'Cañada Fría', 'Salinas del Rey', 'Jardín de Niebla',
                  'Peñasco Gris', 'Manantial Pardo']
ASSET_KINDS = [('vessel', 'Pesquero', 'DEMO-MX'), ('panga', 'Panga', 'DEMO-MX'), ('aircraft', 'Avioneta', 'XB-DEMO'),
               ('tractor-trailer', 'Tráiler', 'DEMO-PLACA'), ('vehicle', 'Camioneta', 'DEMO-PLACA'), ('tanker-truck', 'Pipa', 'DEMO-PLACA')]
ASSET_WORDS = ['Alba Fría', 'Brisa Norte', 'Cielo Pardo', 'Luz Dorada', 'Espuma Gris', 'Gaviota Azul', 'Horizonte Lento', 'Isla Baja',
               'Jade Marino', 'Luna Parda', 'Marea Alta', 'Niebla Roja', 'Oro Viejo', 'Quilla Rota', 'Rumbo Sur', 'Sol Lejano',
               'Tormenta Breve', 'Umbral Azul', 'Vela Blanca', 'Zafiro Lento', 'Coral Frío', 'Delta Hondo', 'Garza Lenta',
               'Halcón Pardo', 'Lince Gris', 'Manta Oscura', 'Nácar Vivo', 'Ola Quieta', 'Pino Marino', 'Ráfaga Corta']
OPERATION_NAMES = ['Brasa Fría', 'Cauce Lento', 'Dique Roto', 'Escarcha Azul', 'Faro Mudo', 'Grano Pardo', 'Hilo Negro', 'Isla Quieta',
                   'Jarra Rota', 'Lastre Gris', 'Muelle Seco', 'Niebla Larga', 'Orilla Fría', 'Peñasco Azul', 'Quilla Corta',
                   'Rastro Lento', 'Sello Pardo', 'Tamiz Fino', 'Umbral Seco', 'Veta Clara', 'Yunque Frío', 'Zanja Honda',
                   'Arena Lenta', 'Bruma Corta', 'Cerco Claro', 'Dársena Gris', 'Eslabón Roto', 'Fosa Azul', 'Grieta Larga',
                   'Herraje Mudo', 'Lonja Fría', 'Marco Pardo', 'Nudo Seco', 'Pleamar Lenta', 'Rizo Gris', 'Surco Claro',
                   'Tejado Roto', 'Viga Azul', 'Costal Vacío', 'Espiga Seca']
MEETING_TOPICS = ['crossing fees', 'a disputed load', 'lane assignments', 'laboratory supply', 'an unpaid debt', 'a rival crew',
                  'port access', 'warehouse space', 'a new courier route', 'the split of a seizure loss']
OFFICIAL_TITLES = {'police': 'the municipal police commander', 'customs': 'a customs supervisor', 'mayor': 'the mayor',
                   'prosecutor': 'a state prosecutor', 'military': 'an army captain'}
EVENT_TYPE_WEIGHTS = [('Shipment', 32), ('Seizure', 16), ('Meeting', 14), ('Payment', 12), ('Arrest', 9), ('Operation', 7),
                     ('Designation', 5), ('Election', 5)]

WORLD_DIR = Path(os.environ['INTELDOC_WORLD_DIR']).resolve() if os.getenv('INTELDOC_WORLD_DIR') else None


def world_dir():
    return WORLD_DIR or ROOT / 'world'


def use_world_dir(path):
    global WORLD_DIR
    WORLD_DIR = Path(path).resolve()


def quantity_text(q):
    return f"{q['value']:,} {q['unit']}" if q else ''


def expand(seed=42, total_events=500):
    bible = yaml.safe_load((ROOT / 'world/seed.yaml').read_text())
    from .seed import validate_seed
    validate_seed(bible)
    rng = random.Random(seed)
    entities, facts = [], []
    by_id = {}

    def add(id, name, kind, place, aliases=None, **fields):
        entity = dict(id=id, name=name, kind=kind, place=place, aliases=aliases or [], **fields)
        entities.append(entity); by_id[id] = entity
        return entity

    def fact(s, p, o, d, u=None):
        f = Fact(subject=s, predicate=p, object=o, date=d, until=u).model_dump(mode='json')
        facts.append(f)
        return f

    # --- places, organizations, corridors ------------------------------------
    places = {p['id']: p for p in bible['geography']['places']}
    place_by_name = {p['name']: p for p in places.values()}
    for p in places.values():
        add(p['id'], p['name'], 'place', p['name'], code=p['code'], state=p['state'], country=p['country'], place_kind=p['kind'])
    for o in bible['organizations']:
        add(o['id'], o['name'], 'organization', places[o['base']]['name'], [o['nickname']], founded=str(o['founded']),
            founding=o['founding'], profile=o['profile'], leadership=o['leadership'], alliances=o['alliances'], fractures=o['fractures'])
    corridors = {c['id']: c for c in bible['corridors']}
    for c in bible['corridors']:
        add(c['id'], c['name'], 'corridor', places[c['places'][0]]['name'], corridor_kind=c['kind'], places=[places[p]['name'] for p in c['places']],
            hubs=[places[p]['name'] for p in c['hubs']], commodities=c['commodities'], control_history=c['control_history'])

    # --- people: authored + generated lower tiers ---------------------------
    for p in bible['people']:
        fields = {k: v for k, v in p.items() if k not in ['id', 'name', 'places', 'aliases']}
        add(p['id'], p['name'], 'person', places[p['places'][0]]['name'], p['aliases'], authored=True,
            places=[places[x]['name'] for x in p['places']], organization=p['membership'][-1]['organization'], **fields)
    taken_names = {e['name'] for e in entities}
    taken_aliases = {a for p in bible['people'] for a in p['aliases']}
    nicknames = [n for n in NICKNAMES if n not in taken_aliases]
    org_ids = [o['id'] for o in bible['organizations']]
    tiers = ['logistics', 'plaza-boss', 'sicario-chief', 'launderer', 'lieutenant', 'logistics']
    generated_people = []
    for i in range(100):
        name = f'{FIRST_NAMES[i % len(FIRST_NAMES)]} {SURNAMES[(i * 7) % len(SURNAMES)]} {SURNAMES[(i * 11 + 5) % len(SURNAMES)]}'
        if name in taken_names:
            name += ' Segundo'
        taken_names.add(name)
        org = by_id[org_ids[i % len(org_ids)]]
        start = max(date.fromisoformat(org['founded']), CORPUS_START + timedelta(days=rng.randrange(0, 365 * 8)))
        surname = name.split()[1]
        aliases = [nicknames[i % len(nicknames)], surname] if surname not in taken_aliases else [nicknames[i % len(nicknames)]]
        taken_aliases.update(aliases)
        person = add(f'person-{i:03}', name, 'person', org['place'], aliases, authored=False, tier=tiers[i % len(tiers)],
                     places=[org['place']], organization=org['id'], membership=[{'organization': org['id'], 'from': str(start), 'to': SENTINEL, 'role': tiers[i % len(tiers)]}])
        generated_people.append(person)
    people = [e for e in entities if e['kind'] == 'person']

    # --- companies, assets, identifiers, sources ---------------------------
    for c in bible['companies']:
        add(c['id'], c['name'], 'company', places[c['places'][0]]['name'], sector=c['sector'], owner=c['owner'], nominee=c.get('nominee'),
            registered=str(c['registered']), places=[places[p]['name'] for p in c['places']])
    sectors = list(COMPANY_PREFIX)
    for i in range(len(bible['companies']), 60):
        sector = sectors[i % len(sectors)]
        name = f'{COMPANY_PREFIX[sector][i % len(COMPANY_PREFIX[sector])]} {COMPANY_SUFFIX[i % len(COMPANY_SUFFIX)]}'
        if name in taken_names:
            name += ' Dos'
        taken_names.add(name)
        owner = rng.choice([p for p in people if p['tier'] in ('launderer', 'lieutenant', 'logistics')])
        add(f'company-{i:03}', name, 'company', owner['place'], sector=sector, owner=owner['id'], nominee=None,
            registered=str(max(date.fromisoformat(owner['membership'][0]['from']), CORPUS_START) + timedelta(days=rng.randrange(30, 900))), places=[owner['place']])
    for a in bible['assets']:
        add(a['id'], a['name'], 'asset', places[a['places'][0]]['name'], asset_kind=a['kind'], registration=a['registration'],
            operator=a['operator'], places=[places[p]['name'] for p in a['places']])
    for i in range(len(bible['assets']), 40):
        kind, prefix, reg = ASSET_KINDS[i % len(ASSET_KINDS)]
        org = by_id[org_ids[i % len(org_ids)]]
        name = f'{prefix} {ASSET_WORDS[i % len(ASSET_WORDS)]}'
        if name in taken_names:
            name += ' Dos'
        taken_names.add(name)
        add(f'asset-{i:03}', name, 'asset', org['place'], asset_kind=kind, registration=f'{reg}-{1000 + i:04}', operator=org['id'], places=[org['place']])
    # Identifiers are deliberately non-dialable / non-bank labels. Some are shared between two people (alias-resolution trap).
    for i in range(360):
        holder = people[(i * 13) % len(people)] if i % 3 else rng.choice([p for p in people if p['authored']])
        start = date.fromisoformat(holder['membership'][0]['from']) + timedelta(days=rng.randrange(0, 1500))
        holders = [{'person': holder['id'], 'from': str(start), 'to': str(start + timedelta(days=rng.randrange(200, 1500)))}]
        if i % 10 == 0:
            other = rng.choice([p for p in people if p['organization'] == holder['organization'] and p['id'] != holder['id']])
            holders.append({'person': other['id'], 'from': holders[0]['to'], 'to': str(date.fromisoformat(holders[0]['to']) + timedelta(days=rng.randrange(200, 1200)))})
        add(f'contact-{i:03}', f'DEMO-{"TEL" if i % 2 else "ACCT"}-{i:05}', 'identifier', holder['place'], holders=holders)
    for s in bible['sources']:
        add(s['id'], s['name'], 'source', places[s['places'][0]]['name'], agency=s['agency'], reliability=s['reliability'], source_kind=s['kind'])

    # --- helpers over the world state --------------------------------------
    def alive(p, when):
        when = str(when)
        if p.get('death_date') and when > str(p['death_date']):
            return False
        if p.get('arrest_date') and when > str(p['arrest_date']):
            return bool(p.get('release_date')) and when >= str(p['release_date'])
        return True

    def member_at(p, org, when):
        return any(m['organization'] == org and m['from'] <= str(when) < m['to'] for m in p['membership'])

    def members(org, when, tiers=None):
        return [p for p in people if member_at(p, org, when) and alive(p, when) and (not tiers or p['tier'] in tiers)]

    def controller_window(corridor_id, when):
        for w in corridors[corridor_id]['control_history']:
            if str(w['from']) <= str(when) < str(w['to']):
                return w
        return None

    def controlled_corridors(org, when):
        return [c for c in corridors if (controller_window(c, when) or {}).get('organization') == org]

    def companies_of(org, when):
        return [c for c in entities if c['kind'] == 'company' and c['registered'] <= str(when) and member_at(by_id[c['owner']], org, when)]

    def assets_of(org):
        return [a for a in entities if a['kind'] == 'asset' and a['operator'] == org]

    def contact_of(p, when):
        held = [c for c in entities if c['kind'] == 'identifier' and any(h['person'] == p['id'] and h['from'] <= str(when) < h['to'] for h in c['holders'])]
        if not held:
            held = [c for c in entities if c['kind'] == 'identifier' and any(h['person'] == p['id'] for h in c['holders'])]
        return held[0] if held else None

    def name(id):
        return by_id[id]['name']

    # --- events: authored beats, then generated routine activity ------------
    events = []
    beats = sorted(bible['timeline'], key=lambda e: str(e['date']))
    for e in beats:
        main = next(part['id'] for part in e['participants'] if part['id'].startswith('p-'))
        company = next((part['id'] for part in e['participants'] if part['id'].startswith('co-')), None)
        asset = next((part['id'] for part in e['participants'] if part['id'].startswith('as-')), None)
        contact = contact_of(by_id[main], e['date'])
        events.append(dict(id=e['id'], type=e['type'], name=e['name'], date=str(e['date']), place=places[e['place']]['name'], place_id=e['place'],
                           org=e['organization'], person=main, participants=e['participants'], corridor=e.get('corridor'), company=company,
                           asset=asset, contact=contact['id'] if contact else None, quantity=e.get('quantity'), description=' '.join(e['description'].split()),
                           seed_event=True))
    beat_dates = [(date.fromisoformat(str(e['date'])), e['organization']) for e in beats]
    total_events = max(total_events, len(events))
    first_founding = min(date.fromisoformat(by_id[o]['founded']) for o in org_ids)
    draws = []
    for i in range(int((total_events - len(events)) * 1.25)):
        if rng.random() < 0.35:
            anchor, org = rng.choice(beat_dates)
            when = anchor + timedelta(days=rng.randrange(-45, 46))
        else:
            when, org = CORPUS_START + timedelta(days=rng.randrange((CORPUS_END - CORPUS_START).days)), None
        when = min(max(when, first_founding), CORPUS_END)
        kind = rng.choices([t for t, _ in EVENT_TYPE_WEIGHTS], weights=[w for _, w in EVENT_TYPE_WEIGHTS])[0]
        draws.append((when, org, kind))
    operation_names = list(OPERATION_NAMES)
    rng.shuffle(operation_names)
    sequence = {}
    for n, (when, org, kind) in enumerate(sorted(draws, key=lambda d: d[0])):
        if len(events) >= total_events:
            break
        existing = [o for o in org_ids if by_id[o]['founded'] <= str(when)]
        org = org if org in existing else rng.choice(existing)
        crew = members(org, when)
        if not crew:
            continue
        corridor_ids = controlled_corridors(org, when)
        corridor = rng.choice(corridor_ids) if corridor_ids and kind in ('Shipment', 'Seizure', 'Operation', 'Payment', 'Meeting') else None
        corridor_places = [places[p] for p in corridors[corridor]['places']] if corridor else []
        base = place_by_name[by_id[org]['place']]
        if kind == 'Shipment':
            place = next((p for p in corridor_places if p['country'] == 'MX' and p['kind'] != 'highway'), corridor_places[0] if corridor_places else base)
        elif kind == 'Seizure':
            crossing = [p for p in corridor_places if p['kind'] in ('border-crossing', 'port')]
            place = rng.choice(crossing) if crossing else base
        else:
            place = rng.choice(corridor_places) if corridor_places and kind in ('Operation', 'Meeting') else base
        tier_pref = {'Shipment': ['logistics', 'plaza-boss'], 'Seizure': ['logistics', 'plaza-boss'], 'Meeting': ['boss', 'lieutenant', 'plaza-boss'],
                     'Payment': ['launderer'], 'Arrest': None, 'Operation': ['plaza-boss', 'sicario-chief'], 'Designation': ['launderer', 'lieutenant'],
                     'Election': ['corrupt-official']}[kind]
        candidates = members(org, when, tier_pref) or crew
        if kind == 'Arrest':
            candidates = [p for p in crew if not p['authored']]
            if not candidates:
                continue
        if kind == 'Election' and not any(p['tier'] == 'corrupt-official' for p in candidates):
            continue
        main = rng.choice(candidates)
        participants = [{'id': main['id'], 'role': 'reported-participant'}, {'id': org, 'role': 'organization'}]
        company = asset = quantity = other = official = None
        year, code = when.year, place['code']
        sequence[(code, year)] = sequence.get((code, year), 0) + 1
        event_name = f'{kind} {code}-{year % 100:02}-{sequence[(code, year)]:02}'
        commodity = rng.choice(corridors[corridor]['commodities']) if corridor else 'cocaine'
        hub = rng.choice(corridors[corridor]['hubs']) if corridor else 'Houston'
        hub_name = places[hub]['name'] if hub in places else hub
        if kind == 'Shipment':
            quantity = {'value': rng.choice([20, 35, 60, 90, 120, 180, 250, 400, 650, 900, 1200]), 'unit': 'kg', 'commodity': commodity}
            if rng.random() < 0.6 and companies_of(org, when):
                company = rng.choice(companies_of(org, when))['id']
            if rng.random() < 0.5 and assets_of(org):
                asset = rng.choice(assets_of(org))['id']
            route = f"along the {name(corridor)}" if corridor else 'by an unreported route'
            description = (f"{main['name']} moved {quantity_text(quantity)} of {commodity} from {place['name']} {route} toward {hub_name}"
                           + (f", using {name(asset)}" if asset else '') + (f", with paperwork from {name(company)}" if company else '') + '.')
        elif kind == 'Seizure':
            quantity = {'value': rng.choice([12, 45, 80, 150, 210, 330, 520, 760, 1100]), 'unit': 'kg', 'commodity': commodity}
            if rng.random() < 0.6 and assets_of(org):
                asset = rng.choice(assets_of(org))['id']
            if rng.random() < 0.4 and companies_of(org, when):
                company = rng.choice(companies_of(org, when))['id']
            description = (f"Inspectors at {place['name']} seized {quantity_text(quantity)} of {commodity}" + (f" hidden in {name(asset)}" if asset else '')
                           + f" and tied the load to {main['name']} of {name(org)}" + (f"; shipping papers named {name(company)}" if company else '') + '.')
        elif kind == 'Meeting':
            partner_org = next((a['with'] for a in by_id[org]['alliances'] if str(a['from']) <= str(when) < str(a['to'])), None)
            pool = members(partner_org, when, ['boss', 'lieutenant', 'plaza-boss']) if partner_org else [p for p in crew if p['id'] != main['id']]
            if pool:
                other = rng.choice(pool)
                participants.append({'id': other['id'], 'role': 'reported-participant'})
                if partner_org:
                    participants.append({'id': partner_org, 'role': 'counterparty'})
            topic = rng.choice(MEETING_TOPICS)
            description = f"{main['name']} met " + (f"{other['name']} " if other else '') + f"in {place['name']} to settle {topic}" + (f" on behalf of {name(org)}" if not partner_org else f" between {name(org)} and {name(partner_org)}") + '.'
        elif kind == 'Payment':
            officials = members(org, when, ['corrupt-official'])
            if not officials:
                continue
            official = rng.choice(officials)
            participants.append({'id': official['id'], 'role': 'payee'})
            quantity = {'value': rng.choice([150000, 300000, 500000, 800000, 1200000, 2000000, 3500000]), 'unit': 'MXN', 'commodity': 'cash'}
            if rng.random() < 0.7 and companies_of(org, when):
                company = rng.choice(companies_of(org, when))['id']
            place = place_by_name[official['place']]
            description = (f"{main['name']} paid {quantity_text(quantity)} in cash to {official['name']}, {OFFICIAL_TITLES[official['official_role']]} in {place['name']},"
                           + (f" through {name(company)}" if company else '') + (f" for protection of the {name(corridor)}" if corridor else ' for protection') + '.')
        elif kind == 'Arrest':
            main['arrest_date'] = str(when)
            for m in main['membership']:
                if m['from'] <= str(when) < m['to']:
                    m['to'] = str(when)
            participants[0]['role'] = 'arrested'
            event_name = f'Arrest {code}-{year % 100:02}-{sequence[(code, year)]:02}'
            description = f"Federal forces arrested {main['name']}, a {main['tier'].replace('-', ' ')} for {name(org)}, in {place['name']}."
        elif kind == 'Operation':
            event_name = 'Operation ' + operation_names[n % len(operation_names)] + ('' if n < len(operation_names) else f' {n // len(operation_names) + 1}')
            if rng.random() < 0.5 and assets_of(org):
                asset = rng.choice(assets_of(org))['id']
            description = (f"Federal forces raided {place['name']} in {event_name}, targeting {name(org)} assets" + (f" including {name(asset)}" if asset else '')
                           + f" tied to {main['name']}.")
        elif kind == 'Designation':
            owned = [c for c in companies_of(org, when) if c['owner'] == main['id']] or companies_of(org, when)
            if not owned:
                continue
            company = rng.choice(owned)['id']
            participants[0]['role'] = 'designated'
            participants.append({'id': company, 'role': 'designated'})
            description = f"Treasury officials designated {name(company)} and {main['name']} as part of the {name(org)} network."
        else:  # Election
            incoming = str(when) <= main['membership'][0]['from'] or rng.random() < 0.5
            participants[0]['role'] = 'incoming-official' if incoming else 'outgoing-official'
            place = place_by_name[main['place']]
            description = (f"{main['name']}, {OFFICIAL_TITLES[main['official_role']]} in {place['name']}, "
                           + ('took office after the municipal election' if incoming else 'left office after the municipal election') + f", a change that favored {name(org)}.")
        if company and not any(part['id'] == company for part in participants):
            participants.append({'id': company, 'role': 'company'})
        if asset:
            participants.append({'id': asset, 'role': 'asset'})
        contact = contact_of(main, when)
        events.append(dict(id=f'event-{len(events):04}', type=kind, name=event_name, date=str(when), place=place['name'], place_id=place['id'],
                           org=org, person=main['id'], participants=participants, corridor=corridor, company=company, asset=asset,
                           contact=contact['id'] if contact else None, quantity=quantity, description=description, seed_event=False))
    events.sort(key=lambda e: (e['date'], e['id']))

    # --- facts: structural edges, then event edges --------------------------
    leadership, membership, ownership, control, alliances = [], [], [], [], []
    for o in bible['organizations']:
        for w in o['leadership']:
            leadership.append({**fact(w['person'], 'leads', o['id'], w['from'], w['to']), 'secret_only': bool(w.get('secret_only'))})
        for a in o['alliances']:
            if o['id'] < a['with']:
                alliances.append(fact(o['id'], 'allied_with', a['with'], a['from'], a['to']))
        if o['founding']['type'] == 'split':
            fact(o['id'], 'split_from', o['founding']['split_from'], o['founded'])
    for p in people:
        for m in p['membership']:
            membership.append(fact(p['id'], 'member_of', m['organization'], m['from'], m['to']))
    for c in entities:
        if c['kind'] == 'company':
            ownership.append(fact(c['owner'], 'owns', c['id'], c['registered']))
            if c.get('nominee'):
                ownership.append(fact(c['nominee'], 'nominee_for', c['id'], c['registered']))
    for c in bible['corridors']:
        for w in c['control_history']:
            control.append(fact(w['organization'], 'controls', c['id'], w['from'], w['to']))
    for e in events:
        add(e['id'], e['name'], 'event', e['place'], event_type=e['type'], date=e['date'], description=e['description'], quantity=e['quantity'])
        seen = set()
        e['facts'] = []
        def plant(s, p, o, d=e['date'], u=None):
            key = (s, p, o)
            if key not in seen:
                seen.add(key); e['facts'].append(fact(s, p, o, d, u))
        main_role = next(part['role'] for part in e['participants'] if part['id'] == e['person'])
        plant(e['person'], ROLE_PREDICATE[main_role], e['id'])
        plant(e['org'], 'linked_to', e['id'])
        plant(e['id'], 'occurred_at', e['place_id'])
        for part in e['participants']:
            if part['id'] in (e['person'], e['org']):
                continue
            plant(part['id'], ROLE_PREDICATE[part['role']], e['id'])
        if e['contact']:
            plant(e['person'], 'uses', e['contact'])
        if e['corridor']:
            plant(e['id'], 'transited', e['corridor'])
            w = controller_window(e['corridor'], e['date'])
            if w:
                plant(w['organization'], 'controls', e['corridor'], w['from'], w['to'])
        if e['type'] in ('Alliance', 'AllianceBreak'):
            a, b = sorted([e['org'], next(part['id'] for part in e['participants'] if part['role'] == 'counterparty')])
            window = next(x for x in by_id[a]['alliances'] if x['with'] == b and (str(x['from']) == e['date'] or str(x['to']) == e['date']))
            plant(a, 'allied_with', b, str(window['from']), str(window['to']))
        if e['type'] == 'Split':
            for o in bible['organizations']:
                if o['founding']['type'] == 'split' and o['founding']['event'] == e['id']:
                    plant(o['id'], 'split_from', o['founding']['split_from'])
        if e['type'] in ('Arrest', 'Killing', 'Extradition', 'Release') and e['seed_event']:
            pass  # status edges are the role predicates above
    unique = {}
    for f in facts:
        unique.setdefault(Fact(**f).key(), f)
    truth = list(unique.values())
    world = dict(schema_version=3, seed=seed, status=bible['status'], notes=bible['notes'], entities=entities, events=events,
                 leadership=leadership, membership=membership, ownership=ownership, control=control, alliances=alliances)
    validate_world(world)
    output = world_dir()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'expanded.json').write_text(json.dumps(world, indent=1, ensure_ascii=False))
    (output / 'graph_truth.json').write_text(json.dumps(truth, indent=1, ensure_ascii=False))
    return world


def validate_world(world):
    ids = [e['id'] for e in world['entities']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate entity ID')
    names = [e['name'] for e in world['entities']]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate entity name')
    known = set(ids)
    by_id = {e['id']: e for e in world['entities']}
    for e in world['events']:
        for f in e['facts']:
            if f['subject'] not in known or f['object'] not in known:
                raise ValueError('Dangling fact')
        for part in [{'id': e['person']}] + e.get('participants', []):
            p = by_id[part['id']]
            if p['kind'] != 'person':
                continue
            if p.get('death_date') and e['date'] > str(p['death_date']):
                raise ValueError('Event after death: ' + e['id'])
            if p.get('arrest_date') and e['date'] > str(p['arrest_date']) and e['type'] not in ('Extradition', 'Release', 'Designation'):
                if not (p.get('release_date') and e['date'] >= str(p['release_date'])):
                    raise ValueError('Event after arrest: ' + e['id'])
    windows = {}
    for f in world['leadership']:
        for lo, hi in windows.setdefault(f['object'], []):
            if f['date'] < hi and f['until'] > lo:
                raise ValueError('Overlapping leadership')
        windows[f['object']].append((f['date'], f['until']))


def load_world():
    path = world_dir() / 'expanded.json'
    return json.loads(path.read_text()) if path.exists() else expand()
