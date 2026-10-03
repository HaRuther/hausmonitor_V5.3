import io,os,sqlite3,shutil
from pathlib import Path
from PIL import Image
DB=Path('/tmp/hm53.db');UP=Path('/tmp/hm53up')
os.environ['DATABASE_PATH']=str(DB);os.environ['UPLOAD_DIR']=str(UP);os.environ['APP_PASSWORD']=''
from fastapi.testclient import TestClient
from app.main import app

def png():
 b=io.BytesIO();Image.new('RGB',(20,20),'white').save(b,'PNG');return b.getvalue()
def setup_module():
 DB.unlink(missing_ok=True);shutil.rmtree(UP,ignore_errors=True)
 # Simulate old key/value settings schema that previously caused startup failure.
 c=sqlite3.connect(DB);c.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)');c.execute("INSERT INTO settings VALUES('base_url','http://192.168.2.62:8000')");c.commit();c.close()
def test_complete_feature_set():
 with TestClient(app) as c:
  assert c.get('/health').json()['version']=='5.3.0'
  assert c.get('/admin').status_code==200
  c.post('/admin/devices',data={'name':'Nedo X32','serial':'123','calibrated_at':'2026-01-01'})
  r=c.post('/level',data={'measured_at':'2026-10-03T10:00','air_temp':'16'},follow_redirects=False);cid=r.headers['location'].split('/')[2]
  c.post(f'/level/{cid}/readings',data={'SW':['1','1.01','.99','1','1'],'SO':['6','6.01','5.99','6','6']})
  c.post(f'/level/{cid}/photo',data={'point':'SW','caption':'Nivellementfoto'},files={'photo':('l.png',png(),'image/png')})
  assert 'Nivellementfoto' in c.get(f'/level/{cid}').text
  c.post(f'/level/{cid}/edit',data={'measured_at':'2026-10-04T10:00','notes':'korrigiert'})
  home=c.get('/');assert 'Automatische Lagebeurteilung' in home.text and 'noise' in home.text and 'Standardabweichung' in home.text
  r=c.post('/cracks',data={'name':'R1','crack_type':'Putzriss','warning_delta':'.3','alarm_delta':'.5'},follow_redirects=False);pid=r.headers['location'].split('/')[2]
  c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-03T11:00','value':'.4'},files={'photo':('a.png',png(),'image/png')})
  c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-04T11:00','value':'.8'},files={'photo':('b.png',png(),'image/png')})
  detail=c.get(f'/cracks/{pid}');assert 'Fotovergleich' in detail.text and 'QR-Code' in detail.text and 'Bearbeiten' in detail.text
  assert c.get(f'/cracks/{pid}/qr.png').status_code==200
  assert c.get('/exports/nivellement.csv').status_code==200 and c.get('/exports/risse.csv').status_code==200
  assert c.get('/reports/all.pdf').content[:4]==b'%PDF'
  assert c.get('/reports/year/2026.pdf').content[:4]==b'%PDF'
  # Verify legacy setting migrated non-destructively.
  db=sqlite3.connect(DB);assert db.execute('SELECT base_url FROM app_settings WHERE id=1').fetchone()[0]=='http://192.168.2.62:8000';assert db.execute("SELECT name FROM sqlite_master WHERE name='settings'").fetchone();db.close()
