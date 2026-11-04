import sqlite3
from contextlib import contextmanager
from .world import ROOT

DB = ROOT/'corpus/manifest.sqlite'

@contextmanager
def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DB,timeout=30)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS cables(id TEXT PRIMARY KEY,state TEXT NOT NULL,record TEXT NOT NULL,error TEXT,attempts INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS evidence(cable TEXT,paragraph INTEGER,subject TEXT,predicate TEXT,object TEXT,date TEXT,until_date TEXT,classification TEXT,controls TEXT,agency TEXT,PRIMARY KEY(cable,paragraph,subject,predicate,object,date,until_date));
    CREATE TABLE IF NOT EXISTS spend(id INTEGER PRIMARY KEY,provider TEXT,operation TEXT,reserved REAL,actual REAL,input_tokens INTEGER,output_tokens INTEGER,status TEXT);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,provider TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
    ''')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
