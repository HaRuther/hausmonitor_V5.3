import csv,hmac,io,os,uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import qrcode
from fastapi import FastAPI,Form,File,UploadFile,Request,HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse,FileResponse,StreamingResponse,Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from PIL import Image
from .database import init_db,con,LEVEL,CRACKS
from .model import POINTS,campaigns,grouped,crack_points,crack_point,settings,assessment
from .reports import make_report
BASE=Path(__file__).parent
@asynccontextmanager
async def life(app):init_db();yield
app=FastAPI(title='Hausmonitor V5.3 LTS',version='5.3.0',lifespan=life);app.add_middleware(SessionMiddleware,secret_key=os.getenv('SECRET_KEY','x'),same_site='lax');app.mount('/static',StaticFiles(directory=BASE/'static'),name='static');tpl=Jinja2Templates(directory=BASE/'templates')
def guard(r):
 if os.getenv('APP_PASSWORD','') and not r.session.get('ok'):return RedirectResponse('/login',303)
def save(raw,typ,prefix,d):
 if typ not in ('image/jpeg','image/png','image/webp'):raise HTTPException(400,'Nur JPG, PNG oder WebP')
 Image.open(io.BytesIO(raw)).verify();ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[typ];n=f'{prefix}-{uuid.uuid4().hex}{ext}';(d/n).write_bytes(raw);return n
@app.get('/health')
def health():return {'status':'ok','version':'5.3.0'}
@app.get('/login',response_class=HTMLResponse)
def loginpage(request:Request):return tpl.TemplateResponse(request=request,name='login.html',context={'error':None})
@app.post('/login')
def login(request:Request,password:str=Form(...)):
 if hmac.compare_digest(password,os.getenv('APP_PASSWORD','')):request.session['ok']=True;return RedirectResponse('/',303)
 return tpl.TemplateResponse(request=request,name='login.html',context={'error':'Passwort falsch'},status_code=401)
@app.post('/logout')
def logout(request:Request):request.session.clear();return RedirectResponse('/login',303)
@app.get('/',response_class=HTMLResponse)
def home(request:Request):
 if (x:=guard(request)):return x
 cs=campaigns();pts=crack_points();st=settings();chart=[{'date':c['measured_at'],'delta':c['stats']['house']['delta'],'se':c['stats']['house']['se'],'low':c['stats']['house']['delta']-c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'high':c['stats']['house']['delta']+c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'sd_sw':c['stats']['SW']['sd'],'sd_so':c['stats']['SO']['sd']} for c in cs]
 warnings=sum(1 for p in pts if p.get('status')=='Warnung');alarms=sum(1 for p in pts if p.get('status')=='Alarm')
 latest_dates=[c.get('measured_at') for c in cs if c.get('measured_at')]+[p['latest'].get('measured_at') for p in pts if p.get('latest') and p['latest'].get('measured_at')]
 latest=max(latest_dates) if latest_dates else None;delta=cs[-1]['stats']['house']['delta'] if cs else None
 level_alarm=st.get('level_alarm',5);level_warn=st.get('level_warn',3)
 overall='alarm' if alarms or (delta is not None and abs(delta)>=level_alarm) else 'warning' if warnings or (delta is not None and abs(delta)>=level_warn) else 'ok'
 overview={'campaigns':len(cs),'points':len(pts),'warnings':warnings,'alarms':alarms,'latest':latest,'overall':overall}
 return tpl.TemplateResponse(request=request,name='home.html',context={'campaigns':cs,'points':pts,'assessment':assessment(cs),'chart':chart,'overview':overview})
@app.get('/level',response_class=HTMLResponse)
def level(request:Request):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='level.html',context={'campaigns':list(reversed(campaigns()))})
@app.get('/level/new',response_class=HTMLResponse)
def levelnew(request:Request):
 if (x:=guard(request)):return x
 with con() as c:dev=[dict(r) for r in c.execute('SELECT * FROM devices ORDER BY name')]
 return tpl.TemplateResponse(request=request,name='level_form.html',context={'c':None,'now':datetime.now().strftime('%Y-%m-%dT%H:%M'),'devices':dev})
@app.post('/level')
def levelcreate(request:Request,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),rainfall_14d:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form(''),device_id:int|None=Form(None)):
 if (x:=guard(request)):return x
 with con() as d:cid=d.execute('INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id)).lastrowid
 return RedirectResponse(f'/level/{cid}/readings',303)
@app.get('/level/{cid}/edit',response_class=HTMLResponse)
def leveledit(request:Request,cid:int):
 if (x:=guard(request)):return x
 with con() as d:c=d.execute('SELECT * FROM campaigns WHERE id=?',(cid,)).fetchone();dev=[dict(r) for r in d.execute('SELECT * FROM devices ORDER BY name')]
 if not c:raise HTTPException(404)
 return tpl.TemplateResponse(request=request,name='level_form.html',context={'c':dict(c),'now':'','devices':dev})
@app.post('/level/{cid}/edit')
def levelupdate(request:Request,cid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),rainfall_14d:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form(''),device_id:int|None=Form(None)):
 if (x:=guard(request)):return x
 with con() as d:d.execute('UPDATE campaigns SET measured_at=?,air_temp=?,wall_temp_sw=?,wall_temp_so=?,groundwater=?,rainfall_14d=?,weather=?,light_mode=?,notes=?,device_id=? WHERE id=?',(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes,device_id,cid))
 return RedirectResponse(f'/level/{cid}',303)
@app.get('/level/{cid}/readings',response_class=HTMLResponse)
def readpage(request:Request,cid:int):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='readings.html',context={'cid':cid,'existing':grouped(cid),'points':POINTS})
@app.post('/level/{cid}/readings')
async def readsave(request:Request,cid:int):
 if (x:=guard(request)):return x
 f=await request.form()
 with con() as d:
  d.execute('DELETE FROM readings WHERE campaign_id=?',(cid,))
  for p in POINTS:
   seq=0
   for raw in f.getlist(p):
    raw=str(raw).strip().replace(',','.')
    if raw:seq+=1;d.execute('INSERT INTO readings(campaign_id,point,sequence,value) VALUES(?,?,?,?)',(cid,p,seq,float(raw)))
 return RedirectResponse(f'/level/{cid}',303)
@app.get('/level/{cid}',response_class=HTMLResponse)
def leveldetail(request:Request,cid:int):
 if (x:=guard(request)):return x
 c=next((z for z in campaigns() if z['id']==cid),None)
 if not c:raise HTTPException(404)
 with con() as d:photos=[dict(r) for r in d.execute('SELECT * FROM level_photos WHERE campaign_id=? ORDER BY id',(cid,))]
 return tpl.TemplateResponse(request=request,name='level_detail.html',context={'c':c,'raw':grouped(cid),'photos':photos})
@app.post('/level/{cid}/photo')
async def levelphoto(request:Request,cid:int,point:str=Form(''),caption:str=Form(''),photo:UploadFile=File(...)):
 if (x:=guard(request)):return x
 n=save(await photo.read(),photo.content_type,f'level-{cid}',LEVEL)
 with con() as d:d.execute('INSERT INTO level_photos(campaign_id,point,filename,caption) VALUES(?,?,?,?)',(cid,point,n,caption))
 return RedirectResponse(f'/level/{cid}',303)
@app.get('/uploads/level/{name}')
def getlevel(request:Request,name:str):
 if (x:=guard(request)):return x
 return FileResponse(LEVEL/Path(name).name)
@app.get('/cracks',response_class=HTMLResponse)
def cracks(request:Request):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='cracks.html',context={'points':crack_points()})
@app.get('/cracks/new',response_class=HTMLResponse)
def cracknew(request:Request):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='crack_form.html',context={'p':None,'defaults':settings()})
@app.post('/cracks')
def crackcreate(request:Request,name:str=Form(...),location:str=Form(''),description:str=Form(''),crack_type:str=Form(''),unit:str=Form('mm'),reference_value:float|None=Form(None),warning_delta:float=Form(.3),alarm_delta:float=Form(.5)):
 if (x:=guard(request)):return x
 with con() as d:pid=d.execute('INSERT INTO crack_points(name,location,description,crack_type,unit,reference_value,warning_delta,alarm_delta) VALUES(?,?,?,?,?,?,?,?)',(name,location,description,crack_type,unit,reference_value,warning_delta,alarm_delta)).lastrowid
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}/edit',response_class=HTMLResponse)
def crackedit(request:Request,pid:int):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='crack_form.html',context={'p':crack_point(pid),'defaults':settings()})
@app.post('/cracks/{pid}/edit')
def crackupdate(request:Request,pid:int,name:str=Form(...),location:str=Form(''),description:str=Form(''),crack_type:str=Form(''),unit:str=Form('mm'),reference_value:float|None=Form(None),warning_delta:float=Form(.3),alarm_delta:float=Form(.5)):
 if (x:=guard(request)):return x
 with con() as d:d.execute('UPDATE crack_points SET name=?,location=?,description=?,crack_type=?,unit=?,reference_value=?,warning_delta=?,alarm_delta=? WHERE id=?',(name,location,description,crack_type,unit,reference_value,warning_delta,alarm_delta,pid))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}',response_class=HTMLResponse)
def crackdetail(request:Request,pid:int):
 if (x:=guard(request)):return x
 p=crack_point(pid)
 if not p:raise HTTPException(404)
 return tpl.TemplateResponse(request=request,name='crack_detail.html',context={'p':p})
@app.get('/cracks/{pid}/new',response_class=HTMLResponse)
def measnew(request:Request,pid:int):
 if (x:=guard(request)):return x
 return tpl.TemplateResponse(request=request,name='crack_measure.html',context={'p':crack_point(pid),'m':None,'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/cracks/{pid}/measurements')
async def meascreate(request:Request,pid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),value:float=Form(...),notes:str=Form(''),photo:UploadFile|None=File(None)):
 if (x:=guard(request)):return x
 n=save(await photo.read(),photo.content_type,f'crack-{pid}',CRACKS) if photo and photo.filename else None
 with con() as d:d.execute('INSERT INTO crack_measurements(crack_point_id,measured_at,air_temp,value,notes,photo_filename) VALUES(?,?,?,?,?,?)',(pid,measured_at,air_temp,value,notes,n))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}/measurements/{mid}/edit',response_class=HTMLResponse)
def measedit(request:Request,pid:int,mid:int):
 if (x:=guard(request)):return x
 with con() as d:m=d.execute('SELECT * FROM crack_measurements WHERE id=? AND crack_point_id=?',(mid,pid)).fetchone()
 return tpl.TemplateResponse(request=request,name='crack_measure.html',context={'p':crack_point(pid),'m':dict(m),'now':''})
@app.post('/cracks/{pid}/measurements/{mid}/edit')
async def measupdate(request:Request,pid:int,mid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),value:float=Form(...),notes:str=Form(''),photo:UploadFile|None=File(None)):
 if (x:=guard(request)):return x
 with con() as d:r=d.execute('SELECT photo_filename FROM crack_measurements WHERE id=?',(mid,)).fetchone();n=r['photo_filename'] if r else None
 if photo and photo.filename:
  if n:(CRACKS/n).unlink(missing_ok=True)
  n=save(await photo.read(),photo.content_type,f'crack-{pid}',CRACKS)
 with con() as d:d.execute('UPDATE crack_measurements SET measured_at=?,air_temp=?,value=?,notes=?,photo_filename=? WHERE id=? AND crack_point_id=?',(measured_at,air_temp,value,notes,n,mid,pid))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/uploads/cracks/{name}')
def getcrack(request:Request,name:str):
 if (x:=guard(request)):return x
 return FileResponse(CRACKS/Path(name).name)
@app.get('/cracks/{pid}/qr.png')
def qr(request:Request,pid:int):
 if (x:=guard(request)):return x
 base=settings().get('base_url') or str(request.base_url).rstrip('/');img=qrcode.make(f'{base}/cracks/{pid}/new');b=io.BytesIO();img.save(b,'PNG');return Response(b.getvalue(),media_type='image/png')
@app.get('/admin',response_class=HTMLResponse)
def admin(request:Request):
 if (x:=guard(request)):return x
 with con() as d:dev=[dict(r) for r in d.execute('SELECT * FROM devices ORDER BY name')]
 return tpl.TemplateResponse(request=request,name='admin.html',context={'s':settings(),'campaigns':campaigns(),'devices':dev})
@app.post('/admin/settings')
def setadmin(request:Request,base_url:str=Form(''),level_info:float=Form(1),level_warn:float=Form(3),level_alarm:float=Form(5),reference_campaign_id:int|None=Form(None),default_crack_warning:float=Form(.3),default_crack_alarm:float=Form(.5)):
 if (x:=guard(request)):return x
 with con() as d:d.execute('UPDATE app_settings SET base_url=?,level_info=?,level_warn=?,level_alarm=?,reference_campaign_id=?,default_crack_warning=?,default_crack_alarm=? WHERE id=1',(base_url,level_info,level_warn,level_alarm,reference_campaign_id,default_crack_warning,default_crack_alarm))
 return RedirectResponse('/admin',303)
@app.post('/admin/devices')
def device(request:Request,name:str=Form(...),serial:str=Form(''),calibrated_at:str=Form(''),notes:str=Form('')):
 if (x:=guard(request)):return x
 with con() as d:d.execute('INSERT INTO devices(name,serial,calibrated_at,notes) VALUES(?,?,?,?)',(name,serial,calibrated_at,notes))
 return RedirectResponse('/admin',303)
@app.get('/exports/nivellement.csv')
def csvlevel(request:Request):
 if (x:=guard(request)):return x
 out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['Datum',*sum(([f'{p}{i}' for i in range(1,6)] for p in POINTS),[])])
 for c in campaigns():g=grouped(c['id']);w.writerow([c['measured_at'],*sum(((g[p]+['']*5)[:5] for p in POINTS),[])])
 return StreamingResponse(iter([out.getvalue()]),media_type='text/csv')
@app.get('/exports/risse.csv')
def csvcrack(request:Request):
 if (x:=guard(request)):return x
 out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['Messstelle','Datum','Temperatur','Messwert','Notiz'])
 for p in crack_points(False):
  for m in p['measurements']:w.writerow([p['name'],m['measured_at'],m['air_temp'],m['value'],m['notes']])
 return StreamingResponse(iter([out.getvalue()]),media_type='text/csv')
@app.get('/reports/all.pdf')
def reportall(request:Request):
 if (x:=guard(request)):return x
 cs=campaigns();return StreamingResponse(make_report(cs,crack_points(False),assessment(cs),LEVEL,CRACKS),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=hausmonitor-bericht.pdf'})
@app.get('/reports/year/{year}.pdf')
def reportyear(request:Request,year:int):
 if (x:=guard(request)):return x
 cs=campaigns();return StreamingResponse(make_report(cs,crack_points(False),assessment(cs),LEVEL,CRACKS,year),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename=hausmonitor-{year}.pdf'})
