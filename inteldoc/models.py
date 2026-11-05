from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Fact(BaseModel):
    subject: str
    predicate: str
    object: str
    date: date
    until: date | None = None

    def key(self):
        return (self.subject, self.predicate, self.object, str(self.date), str(self.until or ''))

class Paragraph(BaseModel):
    number: int
    classification: Literal['U', 'S']
    controls: list[str] = Field(default_factory=list)
    text: str = ''
    facts: list[Fact] = Field(default_factory=list)

    @model_validator(mode='after')
    def marks(self):
        if (self.classification == 'S' and 'FOUO' in self.controls) or (self.classification == 'U' and 'NF' in self.controls):
            raise ValueError('Incompatible classification and dissemination control')
        return self

    @property
    def mark(self):
        return self.classification + ''.join('//'+c for c in sorted(self.controls))

class Cable(BaseModel):
    cable_id: str
    agency: str
    office: str
    report_date: date
    subject: str
    event_id: str
    source_id: str
    reliability: str
    place: str
    keywords: list[str]
    ntk: list[str]
    relevance: Literal['core', 'background']
    paragraphs: list[Paragraph]
    corrects: str | None = None
    disputed: bool = False
    dispute: dict | None = None
    description: str = ''
    quantities: list[str] = Field(default_factory=list)

    @property
    def classification(self):
        return 'S' if any(p.classification == 'S' for p in self.paragraphs) else 'U'

    @property
    def controls(self):
        return sorted({c for p in self.paragraphs for c in p.controls})
