import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from .world import ROOT

DB = Path(os.getenv('INTELDOC_CORPUS_DIR', str(ROOT/'corpus'))).resolve()/'manifest.sqlite'
SPEND_DB = ROOT/'corpus/manifest.sqlite' if os.getenv('INTELDOC_CORPUS_DIR') else None

def data_root():
    return DB.parent

def use_dataset(path):
    global DB, SPEND_DB
    # Retain one spend ledger across different corpus directories.
    if SPEND_DB is None: SPEND_DB = DB
    DB = Path(path).resolve()/'manifest.sqlite'

@contextmanager
def connect_spend():
    with connect(SPEND_DB) as db:
        yield db

@contextmanager
def connect(path=None):
    path = path or DB
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=30)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS cables(id TEXT PRIMARY KEY,state TEXT NOT NULL,record TEXT NOT NULL,error TEXT,attempts INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS evidence(cable TEXT,paragraph INTEGER,subject TEXT,predicate TEXT,object TEXT,date TEXT,until_date TEXT,classification TEXT,controls TEXT,agency TEXT,PRIMARY KEY(cable,paragraph,subject,predicate,object,date,until_date));
    CREATE TABLE IF NOT EXISTS spend(id INTEGER PRIMARY KEY,provider TEXT,operation TEXT,reserved REAL,actual REAL,input_tokens INTEGER,output_tokens INTEGER,status TEXT);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,provider TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS stages(cable TEXT,stage TEXT,payload TEXT,PRIMARY KEY(cable,stage));
    CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS cdr(record_id TEXT PRIMARY KEY,provider TEXT,call_start TEXT,duration_seconds INTEGER,caller_label TEXT,callee_label TEXT,call_type TEXT,caller_person TEXT,callee_person TEXT,caller_window TEXT,callee_window TEXT,handling TEXT);
    CREATE INDEX IF NOT EXISTS cdr_parties ON cdr(caller_person,callee_person,call_start);
    ''')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
