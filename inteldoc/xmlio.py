from datetime import date
from uuid import uuid5, NAMESPACE_URL
from lxml import etree as E
from .world import ROOT

NS=dict(pubs='urn:us:gov:ic:pubs:relaxed',ism='urn:us:gov:ic:ism',irm='urn:us:gov:ic:irm',ntk='urn:us:gov:ic:ntk',cia='urn:us:gov:cia',xlink='http://www.w3.org/1999/xlink')
def q(s):
    prefix,name=s.split(':'); return '{'+NS[prefix]+'}'+name

def attrs(classification,controls,day):
    a={q('ism:classification'):classification,q('ism:ownerProducer'):'USA',q('ism:createDate'):str(day),q('ism:compliesWith'):'ICD-710'}
    if controls:a[q('ism:disseminationControls')]=' '.join(controls)
    if classification=='S':
        a.update({q('ism:classificationReason'):'1.4(c)',q('ism:declassDate'):str(day.replace(year=day.year+25)) if (day.month,day.day)!=(2,29) else str(date(day.year+25,2,28)),q('ism:declassException'):'25X1',q('ism:derivedFrom'):'Unspecified',q('ism:derivativelyClassifiedBy'):'Unspecified'})
    return a

def render(cable):
    a=attrs(cable.classification,cable.controls,cable.report_date)
    root=E.Element(q('pubs:IntelDoc'),nsmap=NS,attrib={**a,'COIProtectionLevel':'3','DESVersion':'5',q('irm:DESVersion'):'3',q('ism:DESVersion'):'5',q('ntk:DESVersion'):'3',q('ism:resourceElement'):'true'})
    def sub(parent,tag,text=None,attrib=None):
        el=E.SubElement(parent,q(tag),attrib=attrib or {}); el.text=text; return el
    ua={q('ism:classification'):'U',q('ism:ownerProducer'):'USA'}
    access=sub(root,'ntk:Access',attrib=ua); profiles=sub(access,'ntk:AccessProfileList',attrib=ua)
    for system,values in [('IC_COI4',[('IC_COI4_DISSEMTO',cable.agency),('IC_COI4_ISSUE','CN')]),('POLICY-URI',[('URI','policy://1000/1-1')])]:
        profile=sub(profiles,'ntk:AccessProfile',attrib=ua); sub(profile,'ntk:AccessSystemName',system,ua)
        for vocab,value in values:sub(profile,'ntk:AccessProfileValue',value,{**ua,q('ntk:vocabulary'):vocab})
    notice=sub(sub(root,'irm:NoticeList',attrib=a),'irm:Notice',attrib={**a,q('irm:nonISMNoticeType'):'BANNER'})
    sub(notice,'irm:NoticeText','SYNTHETIC DEMO ONLY — NO REAL INTELLIGENCE',a)
    pm=sub(sub(root,'pubs:PublicationMetadataList'),'pubs:PublicationMetadata'); admin=sub(pm,'pubs:AdministrativeMetadata')
    identifiers=sub(admin,'pubs:IdentifierList'); sub(identifiers,'pubs:DocumentID',cable.cable_id)
    n=int(cable.cable_id.split('-')[1]); year=cable.report_date.year
    for kind,val in [('IngestionID',f'{n:09}'),('GUIDE',f'guide://{n:04}/{year:06}'),('messagingSystemID',f'{year%100:02}-HQS{n:07}')]:sub(identifiers,'pubs:InternalID',val,{'internalIDtype':kind})
    pub=sub(admin,'pubs:Publisher'); sub(pub,'pubs:AgencyAcronym',attrib={'acronym':cable.agency,'vocabulary':'Nautilus'})
    sub(sub(pub,'pubs:AuthorInfo'),'pubs:OfficeName',cable.office)
    poc=sub(pub,'pubs:POCInfo');sub(poc,'pubs:OfficeName',cable.agency);sub(poc,'pubs:EmailAddress')
    sub(pub,'pubs:AttributionText','Fictional training source',a)
    dates=sub(admin,'pubs:DateList'); stamp=f'{cable.report_date}T12:00:00Z';sub(dates,'pubs:DatePublished',stamp);sub(sub(dates,'pubs:ExtensionElements'),'cia:DateReceived',stamp)
    rights=sub(admin,'pubs:Rights')
    for tag in ['PrivacyActIndicator','CopyrightActIndicator']:sub(rights,'pubs:'+tag,attrib={'indicator':'false'})
    rel=sub(admin,'pubs:Relation'); uid=str(uuid5(NAMESPACE_URL,cable.cable_id))
    for title,path in [('entities','entities'),(cable.cable_id+'.orig',cable.cable_id+'.orig')]:sub(rel,'pubs:AlternateFormat',attrib={q('xlink:href'):f'https://nautilus.example.ic.gov/resource/{uid}/{path}',q('xlink:role'):'https://www.iana.org/assignments/link-relation/alternate',q('xlink:title'):title})
    if cable.corrects:sub(rel,'pubs:OtherRelation',cable.corrects,{'relationType':'corrects'})
    metrics=sub(sub(admin,'irm:ProductionMetricsList',attrib=a),'irm:ProductionMetric',attrib=a)
    for tag in ['ProductionMetricsSubject','ProductionMetricsCoverage']:sub(metrics,'irm:'+tag,'Unspecified',a)
    sub(admin,'pubs:OtherProperty','0',{'qualifier':'DocumentPrecedence'})
    sub(admin,'pubs:OtherProperty',f'{cable.agency} SYNTHETIC IIR',{'qualifier':'HEADER'})
    ext=sub(sub(admin,'pubs:ExtensionElements'),'cia:AdminstrativeMetadataExtensions');sub(ext,'cia:DocumentStatus','ACTIVE');sub(ext,'cia:OrigintingSystem','LEGACY')
    desc=sub(pm,'pubs:DescriptiveMetadata'); mark=cable.classification+''.join('//'+c for c in cable.controls)
    sub(desc,'pubs:Title',f'SUBJ: ({mark}) {cable.subject}',a);sub(desc,'pubs:Language','eng',{'encoding':'ISO639-3'});sub(desc,'pubs:Description','Synthetic demonstration record',a)
    geo=sub(sub(sub(desc,'pubs:Coverage'),'pubs:GeospatialExtent'),'pubs:GeographicIdentifier');sub(geo,'pubs:PlaceName',cable.place,a)
    keywords=sub(desc,'pubs:Subject')
    for keyword in cable.keywords:sub(keywords,'pubs:Keyword',keyword)
    sub(sub(desc,'pubs:IntelType'),'pubs:IntelDiscipline','OSINT' if cable.agency=='OSINT' else 'HUMINT')
    sub(desc,'pubs:ProductLine','Unspecified',{'qualifier':'true'})
    source=sub(sub(sub(desc,'pubs:CollectSourceList'),'pubs:CollectSource'),'pubs:CollectSourceDescription')
    sub(source,'pubs:Para',f'SOURCE: {cable.source_id} CONTEXT: {cable.reliability}',a)
    sub(sub(sub(desc,'pubs:ExtensionElements'),'cia:DescriptiveMetaDataExtensions'),'cia:Collection','CC')
    body=sub(root,'pubs:DocumentBody',attrib=a)
    text=f'SUBJ: ({mark}) {cable.subject}\n\n'+'\n\n'.join(f'{p.number}. ({p.mark}) {p.text}' for p in cable.paragraphs)
    text+=f'\nTOPIC: CN\nREQUIREMENT: DEMO\nDATE OF ACQUISITION: {cable.report_date}\nPOC: {cable.office}\nWARNING: FICTIONAL TRAINING DATA\nAGENCY: {cable.agency}\nDECLASSIFY ON: {a.get(q("ism:declassDate"),"N/A")}\nEND OF MESSAGE {mark}'
    sub(body,'pubs:PreformattedText',text,a)
    xml=E.tostring(root,encoding='utf-8',xml_declaration=True,pretty_print=True)
    parsed=E.fromstring(xml,E.XMLParser(resolve_entities=False,no_network=True))
    schema_path=ROOT/'schemas/pubs.xsd'
    if schema_path.exists():E.XMLSchema(E.parse(str(schema_path))).assertValid(parsed)
    sch=ROOT/'schemas/pubs.sch'
    if sch.exists():
        from lxml.isoschematron import Schematron
        if not Schematron(E.parse(str(sch))).validate(parsed):raise ValueError('Schematron validation failed')
    return xml
