import os,sqlite3
from pathlib import Path
from contextlib import contextmanager
DB=Path(os.getenv('DATABASE_PATH','/data/hausmonitor.db'));UPLOAD=Path(os.getenv('UPLOAD_DIR','/data/uploads'));LEVEL=UPLOAD/'level';CRACKS=UPLOAD/'cracks'
SCHEMA='''
CREATE TABLE IF NOT EXISTS app_settings(id INTEGER PRIMARY KEY CHECK(id=1),base_url TEXT DEFAULT '',level_info REAL DEFAULT 1,level_warn REAL DEFAULT 3,level_alarm REAL DEFAULT 5,reference_campaign_id INTEGER,default_crack_warning REAL DEFAULT .3,default_crack_alarm REAL DEFAULT .5);
CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,serial TEXT,calibrated_at TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS campaigns(id INTEGER PRIMARY KEY AUTOINCREMENT,measured_at TEXT NOT NULL,air_temp REAL,wall_temp_sw REAL,wall_temp_so REAL,groundwater REAL,rainfall_14d REAL,weather TEXT,light_mode TEXT,notes TEXT,device_id INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY AUTOINCREMENT,campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,point TEXT NOT NULL,sequence INTEGER NOT NULL,value REAL NOT NULL,UNIQUE(campaign_id,point,sequence));
CREATE TABLE IF NOT EXISTS level_photos(id INTEGER PRIMARY KEY AUTOINCREMENT,campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,point TEXT,filename TEXT NOT NULL,caption TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS crack_points(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,location TEXT,description TEXT,crack_type TEXT,unit TEXT DEFAULT 'mm',reference_value REAL,warning_delta REAL DEFAULT .3,alarm_delta REAL DEFAULT .5,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS crack_measurements(id INTEGER PRIMARY KEY AUTOINCREMENT,crack_point_id INTEGER NOT NULL REFERENCES crack_points(id) ON DELETE CASCADE,measured_at TEXT NOT NULL,air_temp REAL,value REAL NOT NULL,notes TEXT,photo_filename TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
'''
def init_db():
 DB.parent.mkdir(parents=True,exist_ok=True);LEVEL.mkdir(parents=True,exist_ok=True);CRACKS.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(DB) as c:
  c.execute('PRAGMA foreign_keys=ON');c.executescript(SCHEMA);c.execute('INSERT OR IGNORE INTO app_settings(id) VALUES(1)')
  # Migration aus älteren Versionen, einschließlich settings(key,value)
  tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if 'settings' in tables:
   cols={r[1] for r in c.execute('PRAGMA table_info(settings)')}
   if {'key','value'}<=cols:
    legacy=dict(c.execute('SELECT key,value FROM settings'))
    mapping={'base_url':'base_url','level_info':'level_info','level_warn':'level_warn','level_alarm':'level_alarm','reference_campaign_id':'reference_campaign_id','default_crack_warning':'default_crack_warning','default_crack_alarm':'default_crack_alarm'}
    for k,col in mapping.items():
     if k in legacy:
      try:c.execute(f'UPDATE app_settings SET {col}=? WHERE id=1',(legacy[k],))
      except sqlite3.Error:pass
  for table,defs in {'campaigns':[('rainfall_14d','REAL'),('device_id','INTEGER'),('light_mode','TEXT')],'crack_points':[('crack_type','TEXT'),('warning_delta','REAL DEFAULT .3'),('alarm_delta','REAL DEFAULT .5'),('active','INTEGER DEFAULT 1')]}.items():
   cols={r[1] for r in c.execute(f'PRAGMA table_info({table})')}
   for n,t in defs:
    if n not in cols:c.execute(f'ALTER TABLE {table} ADD COLUMN {n} {t}')
@contextmanager
def con():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:yield c;c.commit()
 finally:c.close()
