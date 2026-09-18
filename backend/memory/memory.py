import json
import sqlite3
import threading
from datetime import datetime, timezone

class Memory:
    def __init__(self,path):
        self.path=str(path); self.lock=threading.RLock()
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS objects (kind TEXT, id TEXT, data TEXT, PRIMARY KEY(kind,id))')
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, time TEXT, stage TEXT, data TEXT)')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30)
        db.execute('PRAGMA journal_mode=WAL'); return db
    def put(self,kind,id,data):
        with self.lock,self.connect() as db: db.execute('INSERT OR REPLACE INTO objects VALUES (?,?,?)',(kind,id,json.dumps(data)))
    def get(self,kind,id):
        with self.connect() as db: row=db.execute('SELECT data FROM objects WHERE kind=? AND id=?',(kind,id)).fetchone()
        if not row: raise KeyError(id)
        return json.loads(row[0])
    def list(self,kind):
        with self.connect() as db: return [json.loads(r[0]) for r in db.execute('SELECT data FROM objects WHERE kind=? ORDER BY rowid DESC',(kind,))]
    def event(self,task,stage,data):
        with self.lock,self.connect() as db:
            db.execute('INSERT INTO events(task,time,stage,data) VALUES (?,?,?,?)',(task,datetime.now(timezone.utc).isoformat(),stage,json.dumps(data)))
    def events(self,task):
        with self.connect() as db:
            return [{'seq':r[0],'time':r[1],'stage':r[2],'data':json.loads(r[3])} for r in db.execute('SELECT seq,time,stage,data FROM events WHERE task=? ORDER BY seq',(task,))]
