from math import sqrt
from statistics import mean,stdev
from .database import con
POINTS=('SW','SO','ANB','TSW','TSO')
def summ(v):
 if not v:return {'n':0,'mean':None,'sd':None,'se':None,'range':None}
 sd=stdev(v) if len(v)>1 else None;return {'n':len(v),'mean':mean(v),'sd':sd,'se':sd/sqrt(len(v)) if sd is not None else None,'range':max(v)-min(v)}
def grouped(cid):
 g={p:[] for p in POINTS}
 with con() as c:
  for r in c.execute('SELECT point,value FROM readings WHERE campaign_id=? ORDER BY sequence',(cid,)):g.setdefault(r['point'],[]).append(r['value'])
 return g
def pair(a,b,base):
 if a['mean'] is None or b['mean'] is None:return {'value':None,'se':None,'delta':None,'snr':None,'quality':'unvollständig'}
 v=b['mean']-a['mean'];se=sqrt(a['se']**2+b['se']**2) if a['se'] is not None and b['se'] is not None else None;d=v-base if base is not None else None;snr=abs(d)/se if d is not None and se else None
 q='Signal klar' if snr is not None and snr>=3 else 'Hinweis' if snr is not None and snr>=2 else 'im Rauschen' if snr is not None else 'nicht bewertbar'
 return {'value':v,'se':se,'delta':d,'snr':snr,'quality':q}
def settings():
 with con() as c:return dict(c.execute('SELECT * FROM app_settings WHERE id=1').fetchone())
def campaigns():
 with con() as c:rows=[dict(r) for r in c.execute('SELECT campaigns.*,devices.name device_name FROM campaigns LEFT JOIN devices ON devices.id=campaigns.device_id ORDER BY measured_at,id')]
 st=settings();tmp=[]
 for r in rows:tmp.append((r,{p:summ(grouped(r['id'])[p]) for p in POINTS}))
 rid=st.get('reference_campaign_id')
 base=next((o['SO']['mean']-o['SW']['mean'] for r,o in tmp if (not rid or r['id']==rid) and o['SW']['mean'] is not None and o['SO']['mean'] is not None),None)
 anb_base=next((o['ANB']['mean']-o['SW']['mean'] for r,o in tmp if (not rid or r['id']==rid) and o['SW']['mean'] is not None and o['ANB']['mean'] is not None),None)
 tb=next((o['TSO']['mean']-o['TSW']['mean'] for _,o in tmp if o['TSW']['mean'] is not None and o['TSO']['mean'] is not None),None)
 out=[]
 for r,o in tmp:
  o['house']=pair(o['SW'],o['SO'],base);o['anb_sw']=pair(o['SW'],o['ANB'],anb_base);o['terrace']=pair(o['TSW'],o['TSO'],tb);r['stats']=o;out.append(r)
 return out
def assessment(cs):
 if not cs:return 'Es liegen noch keine Nivellement-Messreihen vor.'
 h=cs[-1]['stats']['house'];d=h['delta'];se=h['se'];snr=h['snr']
 if d is None:return 'Die aktuelle Messreihe ist unvollständig. Für die Hausdifferenz werden SW- und SO-Rohwerte benötigt.'
 if snr is None:return f'Die aktuelle Änderung beträgt {d:+.3f} mm. Das Messrauschen ist mit den vorhandenen Rohwerten noch nicht belastbar bestimmbar.'
 text=f'Die aktuelle Änderung beträgt {d:+.3f} mm gegenüber der Referenz. Der kombinierte Standardfehler beträgt {se:.3f} mm; das Signal-Rausch-Verhältnis liegt bei {snr:.2f}. '
 return text+('Die Änderung liegt deutlich über dem rechnerischen Messrauschen und sollte durch weitere Kampagnen bestätigt werden.' if snr>=3 else 'Die Änderung ist ein Hinweis und sollte weiter beobachtet werden.' if snr>=2 else 'Die Änderung liegt derzeit im Bereich des rechnerischen Messrauschens.')
def crack_point(pid):
 with con() as c:
  p=c.execute('SELECT * FROM crack_points WHERE id=?',(pid,)).fetchone()
  if not p:return None
  p=dict(p);p['measurements']=[dict(r) for r in c.execute('SELECT * FROM crack_measurements WHERE crack_point_id=? ORDER BY measured_at,id',(pid,))]
 base=p['measurements'][0]['value'] if p['measurements'] else p['reference_value']
 for m in p['measurements']:m['delta']=m['value']-base if base is not None else None
 p['baseline']=base;p['latest']=p['measurements'][-1] if p['measurements'] else None;p['delta']=p['latest']['value']-base if p['latest'] and base is not None else None;p['first_photo']=next((m for m in p['measurements'] if m['photo_filename']),None);p['latest_photo']=next((m for m in reversed(p['measurements']) if m['photo_filename']),None)
 p['status']='Alarm' if p['delta'] is not None and abs(p['delta'])>=p['alarm_delta'] else 'Warnung' if p['delta'] is not None and abs(p['delta'])>=p['warning_delta'] else 'Stabil'
 return p
def crack_points(active=True):
 with con() as c:ids=[r[0] for r in c.execute('SELECT id FROM crack_points '+('WHERE active=1' if active else '')+' ORDER BY name')]
 return [crack_point(i) for i in ids]
