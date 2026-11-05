import hashlib,json,sqlite3,tarfile
from pathlib import Path
from lxml import etree as E
from inteldoc.models import Cable,Fact
from inteldoc.pipeline import check,extract
from inteldoc.xmlio import render,NS,q
root=Path('/workspace/kg-dea'); out=root/'corpus/api-pilot'
world=json.loads((root/'world/pilot/expanded.json').read_text())
truth={Fact(**f).key() for f in json.loads((root/'world/pilot/graph_truth.json').read_text())}
db=sqlite3.connect(out/'manifest.sqlite');db.row_factory=sqlite3.Row
ledger=sqlite3.connect(root/'corpus/manifest.sqlite')
checks=[];claimed=set();planted=set();all_claims=0;missing=[]
for row in db.execute("select * from cables where state='validated' order by rowid"):
 c=Cable.model_validate_json(row['record']);check(c,world)
 stem=f"{int(c.cable_id.split('-')[1]):04}-{c.report_date.year:06}"
 xml=(out/f'xml/{stem}.xml').read_bytes();tree=E.fromstring(xml,E.XMLParser(resolve_entities=False,no_network=True))
 assert xml==render(c),c.cable_id+' XML differs from record'
 assert Cable.model_validate_json((out/f'truth/{stem}.json').read_text())==c
 assert tree.find('.//pubs:DocumentID',NS).text==c.cable_id
 assert tree.get(q('ism:classification'))==c.classification
 ps={p.number:p for p in c.paragraphs}
 payload=db.execute("select payload from stages where cable=? and stage='extract'",(c.cable_id,)).fetchone()
 assert payload
 claims=json.loads(payload[0])['claims'];expected=set()
 for claim in claims:
  p=ps[claim['paragraph']];f=Fact(**{k:v for k,v in claim.items() if k not in ['paragraph','quote']})
  assert claim['quote'] in p.text
  assert f.key() in {x.key() for x in extract(claim['quote'],world)}
  assert f.key() in truth
  expected.add((c.cable_id,p.number,*f.key(),p.classification,','.join(p.controls),c.agency))
 actual={tuple(r) for r in db.execute('select * from evidence where cable=?',(c.cable_id,))}
 assert actual==expected,c.cable_id+' evidence differs from cited extraction'
 for p in c.paragraphs:
  recovered={tuple(r)[2:7] for r in actual if r[1]==p.number}
  wanted={f.key() for f in p.facts};planted.update(wanted)
  for f in wanted-recovered:missing.append({'cable':c.cable_id,'paragraph':p.number,'fact':f})
 claimed.update(r[2:7] for r in expected);all_claims+=len(expected)
 checks.append(c.cable_id)
with tarfile.open(root/'artifacts/pilot-recovery-2026-11-05.tar.gz') as tar:
 index=json.load(tar.extractfile('recovery.json'))
 preserved={p:hashlib.sha256((root/p).read_bytes()).hexdigest()==index['files'][p]['sha256'] for p in ['world/pilot/expanded.json','world/pilot/graph_truth.json','world/expanded.json','world/graph_truth.json','corpus/api-pilot/selection.json']}
assert all(preserved.values())
beyond=db.execute("select count(*) from cables where cast(substr(id,instr(id,'-')+1,6) as integer)>50 and attempts>0").fetchone()[0];assert beyond==0
settled,reserved,total,requests=ledger.execute('select coalesce(sum(actual),0),coalesce(sum(case when actual is null then reserved else 0 end),0),coalesce(sum(coalesce(actual,reserved)),0),count(*) from spend').fetchone()
report={'successful_documents':len(checks),'states':dict(db.execute('select state,count(*) from cables group by state')),'xml_files':len(list((out/'xml').glob('*.xml'))),'xml_and_record_checks_passed':len(checks),'extracted_fact_citations_verified':all_claims,'unique_extracted_facts':len(claimed),'unique_planted_facts':len(planted),'precision':len(claimed&truth)/len(claimed) if claimed else None,'planted_recall':len(claimed&planted)/len(planted) if planted else None,'omitted_planted_facts':missing,'settled_api_spend_usd':settled,'unsettled_reservations_usd':reserved,'accounted_api_spend_usd':total,'request_reservations':requests,'cap_usd':5,'beyond_first_50_attempted':beyond,'preserved_artifacts':preserved,'official_schema_validation':'Unavailable: no XSD or Schematron package is bundled','errors':[dict(r) for r in db.execute('select id,error from cables where state="failed"')]}
assert total<5
(out/'run-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['omitted_planted_facts','preserved_artifacts']},indent=2))
