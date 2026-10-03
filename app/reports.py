from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle,getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image as RImage

BLUE='#17365d';ACCENT='#2878cc';GREEN='#059669';ORANGE='#d97706';RED='#c62828';MUTED='#667085'
BASE=Path(__file__).resolve().parent

def f(v,n=3):return '–' if v is None else f'{v:.{n}f}'
def esc(v):return str(v if v is not None else '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def dt(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00'))
 except (ValueError,TypeError):return None

def styles():
 s=getSampleStyleSheet();s.add(ParagraphStyle(name='Cover',parent=s['Title'],fontSize=28,leading=32,textColor=colors.HexColor(BLUE),alignment=TA_CENTER));s.add(ParagraphStyle(name='Sub',parent=s['Normal'],fontSize=14,leading=18,textColor=colors.HexColor(MUTED),alignment=TA_CENTER));s.add(ParagraphStyle(name='Caption',parent=s['Normal'],fontSize=7.5,leading=9,textColor=colors.HexColor(MUTED),alignment=TA_CENTER));s.add(ParagraphStyle(name='Small',parent=s['Normal'],fontSize=8,leading=10,textColor=colors.HexColor(MUTED)));s['Heading1'].textColor=colors.HexColor(BLUE);s['Heading2'].textColor=colors.HexColor(BLUE);s['Heading3'].textColor=colors.HexColor(BLUE);return s

def tab(rows,widths=None):
 t=Table(rows,repeatRows=1,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(BLUE)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#9aa7b4')),('FONTSIZE',(0,0),(-1,-1),7.5),('LEADING',(0,0),(-1,-1),9),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7fa')]),('PADDING',(0,0),(-1,-1),4)]));return t

def fig_image(fig,h=78*mm):
 b=BytesIO();fig.savefig(b,format='png',dpi=170,bbox_inches='tight',facecolor='white');plt.close(fig);b.seek(0);im=RImage(b,width=181*mm,height=h);im._buffer=b;return im

def axis(ax):
 loc=mdates.AutoDateLocator(minticks=3,maxticks=8);ax.xaxis.set_major_locator(loc);ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc));ax.grid(True,axis='y',color='#d9e1ea',linewidth=.7);ax.spines[['top','right']].set_visible(False);ax.tick_params(labelsize=8)

def level_chart(cs):
 r=[]
 for c in cs:
  d=dt(c.get('measured_at'));h=c.get('stats',{}).get('house',{});v=h.get('delta');se=h.get('se')
  if d and v is not None:r.append((d,float(v),float(se) if se is not None else 0))
 if not r:return None
 r.sort();x=[z[0] for z in r];y=[z[1] for z in r];lo=[z[1]-z[2] for z in r];hi=[z[1]+z[2] for z in r]
 fig,ax=plt.subplots(figsize=(8.6,3.6));ax.fill_between(x,lo,hi,color='#7fc3ff',alpha=.35,label='± Standardfehler');ax.plot(x,y,color=ACCENT,lw=2.2,marker='o',label='Änderung Haus');ax.axhline(0,color='#59636e',lw=.9);ax.set_title('Hausänderung gegenüber der Referenz');ax.set_ylabel('Änderung [mm]');axis(ax);ax.legend(frameon=False,fontsize=8);fig.tight_layout();return fig_image(fig)

def sd_chart(cs):
 r=[]
 for c in cs:
  d=dt(c.get('measured_at'));st=c.get('stats',{});a=st.get('SW',{}).get('sd');b=st.get('SO',{}).get('sd')
  if d and (a is not None or b is not None):r.append((d,a,b))
 if not r:return None
 r.sort();x=[z[0] for z in r];a=[float('nan') if z[1] is None else z[1] for z in r];b=[float('nan') if z[2] is None else z[2] for z in r]
 fig,ax=plt.subplots(figsize=(8.6,3.4));ax.plot(x,a,color=GREEN,lw=2,marker='o',label='SD SW');ax.plot(x,b,color=ORANGE,lw=2,marker='o',label='SD SO');ax.set_title('Standardabweichung der Rohmessungen');ax.set_ylabel('SD [mm]');axis(ax);ax.legend(frameon=False,fontsize=8);fig.tight_layout();return fig_image(fig,74*mm)

def crack_chart(p):
 r=[]
 for m in p.get('measurements',[]):
  d=dt(m.get('measured_at'));v=m.get('value')
  if d and v is not None:r.append((d,float(v)))
 if not r:return None
 r.sort();x=[z[0] for z in r];y=[z[1] for z in r];base=float(p.get('baseline') if p.get('baseline') is not None else y[0]);w=p.get('warning_delta');a=p.get('alarm_delta')
 fig,ax=plt.subplots(figsize=(8.6,3.3));ax.plot(x,y,color=ACCENT,lw=2.2,marker='o',label='Messwert');ax.axhline(base,color='#59636e',ls='--',lw=1,label='Referenz')
 if w is not None:
  w=abs(float(w));ax.axhline(base+w,color=ORANGE,ls='--',lw=1,label='Warnung');ax.axhline(base-w,color=ORANGE,ls='--',lw=1)
 if a is not None:
  a=abs(float(a));ax.axhline(base+a,color=RED,ls=':',lw=1,label='Alarm');ax.axhline(base-a,color=RED,ls=':',lw=1)
 ax.set_title('Rissverlauf: '+str(p.get('name','Messstelle')));ax.set_ylabel('Messwert ['+str(p.get('unit') or 'mm')+']');axis(ax);ax.legend(frameon=False,fontsize=7.5,ncol=2);fig.tight_layout();return fig_image(fig,72*mm)

def image(path,w=82*mm,h=58*mm):
 try:
  im=RImage(str(path));im._restrictSize(w,h);return im
 except Exception:return None

def period(cs,pts):
 d=[dt(c.get('measured_at')) for c in cs]+[dt(m.get('measured_at')) for p in pts for m in p.get('measurements',[])];d=[x for x in d if x];return f'{min(d):%d.%m.%Y} bis {max(d):%d.%m.%Y}' if d else 'Keine datierten Messungen'

def summary(cs,pts):
 warnings=sum(1 for p in pts if p.get('status')=='Warnung');alarms=sum(1 for p in pts if p.get('status')=='Alarm');latest=cs[-1].get('stats',{}).get('house',{}).get('quality') if cs else '–';status='Handlungsbedarf' if alarms else 'Beobachten' if warnings else 'Stabil';color=RED if alarms else ORANGE if warnings else GREEN;return warnings,alarms,latest,status,color

def footer(canvas,doc):
 canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d9e1ea'));canvas.line(12*mm,10*mm,A4[0]-12*mm,10*mm);canvas.setFont('Helvetica',7.5);canvas.setFillColor(colors.HexColor(MUTED));canvas.drawString(12*mm,6*mm,'Hausmonitor Monitoringbericht');canvas.drawRightString(A4[0]-12*mm,6*mm,f'Seite {doc.page}');canvas.restoreState()

def make_report(cs,pts,assessment,level_dir,crack_dir,year=None):
 cs=list(cs);pts=list(pts)
 if year:
  cs=[c for c in cs if str(c.get('measured_at','')).startswith(str(year))];pts=[dict(p,measurements=[m for m in p.get('measurements',[]) if str(m.get('measured_at','')).startswith(str(year))]) for p in pts]
 s=styles();b=BytesIO();doc=SimpleDocTemplate(b,pagesize=A4,rightMargin=12*mm,leftMargin=12*mm,topMargin=13*mm,bottomMargin=14*mm,title=f'Hausmonitor Bericht {year or ""}',author='Hausmonitor');story=[];warnings,alarms,quality,status,status_color=summary(cs,pts)
 logo=next((q for q in [BASE/'static/icons/icon-192.png',BASE/'static/icons/icon-512.png'] if q.exists()),None)
 story.append(Spacer(1,10*mm))
 if logo:
  im=image(logo,32*mm,32*mm)
  if im:im.hAlign='CENTER';story+=[im,Spacer(1,5*mm)]
 story+=[Paragraph('HAUSMONITOR',s['Cover']),Spacer(1,2*mm),Paragraph(f'Monitoringbericht{" "+str(year) if year else ""}',s['Sub']),Spacer(1,8*mm)]
 meta=Table([['Berichtszeitraum',period(cs,pts)],['Erstellt am',datetime.now().strftime('%d.%m.%Y %H:%M')],['Nivellement-Messreihen',len(cs)],['Rissmessstellen',len(pts)]],colWidths=[62*mm,90*mm],hAlign='CENTER');meta.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eaf2fb')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor(BLUE)),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#c8d4df')),('PADDING',(0,0),(-1,-1),8)]));story+=[meta,Spacer(1,8*mm)]
 state=Table([[Paragraph('Gesamtstatus',s['Small']),Paragraph(f'<b>{status}</b>',s['Heading2'])]],colWidths=[50*mm,102*mm],hAlign='CENTER');state.setStyle(TableStyle([('BOX',(0,0),(-1,-1),1.2,colors.HexColor(status_color)),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f7fafc')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('PADDING',(0,0),(-1,-1),8)]));story+=[state,Spacer(1,7*mm),Paragraph('Automatische Lagebeurteilung',s['Heading2']),Paragraph(esc(assessment),s['BodyText']),Spacer(1,8*mm)]
 kpi=Table([['Messreihen','Messstellen','Warnungen','Alarme'],[len(cs),len(pts),warnings,alarms]],colWidths=[38*mm]*4,hAlign='CENTER');kpi.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(BLUE)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTSIZE',(0,1),(-1,1),16),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#c8d4df')),('PADDING',(0,0),(-1,-1),7)]));story+=[kpi,Spacer(1,8*mm),Paragraph('Hinweis: Statistische Bewertungen unterstützen das Monitoring, ersetzen aber keine bautechnische oder geotechnische Begutachtung.',s['Small']),PageBreak()]
 story+=[Paragraph('Inhaltsverzeichnis',s['Heading1']),Paragraph('1. Management-Zusammenfassung ........................................ 1',s['BodyText']),Paragraph('2. Nivellement ................................................................ 3',s['BodyText']),Paragraph('3. Rissmonitoring ............................................................ nach Nivellement',s['BodyText']),Paragraph('4. Dokumentationshinweis ............................................... Schlussseite',s['BodyText']),PageBreak(),Paragraph('2. Nivellement',s['Heading1'])]
 if cs:
  rows=[['Datum','Haus','Δ','SE','SNR','Terrasse','GW','Luft']]
  for c in cs:
   st=c.get('stats',{});h=st.get('house',{});t=st.get('terrace',{});rows.append([str(c.get('measured_at','')).replace('T',' '),f(h.get('value')),f(h.get('delta')),f(h.get('se')),f(h.get('snr'),2),f(t.get('value')),f(c.get('groundwater')),f(c.get('air_temp'),1)])
  story+=[tab(rows,[32*mm,20*mm,18*mm,18*mm,17*mm,22*mm,18*mm,17*mm]),Spacer(1,5*mm)]
  for title,ch in [('2.1 Änderung mit Fehlerband',level_chart(cs)),('2.2 Messstreuung',sd_chart(cs))]:
   if ch:story+=[Paragraph(title,s['Heading2']),ch,Spacer(1,4*mm)]
 else:story.append(Paragraph('Keine Nivellement-Messreihen im gewählten Zeitraum.',s['BodyText']))
 story+=[PageBreak(),Paragraph('3. Rissmonitoring',s['Heading1']),Paragraph('Legende: Grün = stabil, Orange = Warnung/Beobachtung, Rot = Alarm/Handlungsbedarf. Diagrammlinien zeigen Referenz sowie Warn- und Alarmgrenzen.',s['Small']),Spacer(1,4*mm)]
 for i,p in enumerate(pts,1):
  if i>1:story.append(PageBreak())
  story+=[Paragraph(f'3.{i} {esc(p.get("name") or "Messstelle")}',s['Heading2']),Paragraph(f'Ort: {esc(p.get("location") or "–")} · Art: {esc(p.get("crack_type") or "–")} · Status: {esc(p.get("status") or "–")} · Änderung: {f(p.get("delta"))} {esc(p.get("unit") or "mm")}',s['BodyText']),Spacer(1,3*mm)]
  ch=crack_chart(p)
  if ch:story+=[ch,Spacer(1,3*mm)]
  ms=p.get('measurements',[]);rows=[['Datum','Temp.','Wert','Δ','Notiz']]+[[str(m.get('measured_at','')).replace('T',' '),f(m.get('air_temp'),1),f(m.get('value')),f(m.get('delta')),Paragraph(esc(m.get('notes') or ''),s['Small'])] for m in ms];story+=[tab(rows,[38*mm,18*mm,21*mm,21*mm,76*mm]),Spacer(1,4*mm)]
  photos=[m for m in ms if m.get('photo_filename') and (Path(crack_dir)/m['photo_filename']).exists()]
  if photos:
   first,last=photos[0],photos[-1];a=image(Path(crack_dir)/first['photo_filename']);z=image(Path(crack_dir)/last['photo_filename']);cells=[]
   for im,label in [(a,'Erstes Foto · '+str(first.get('measured_at','')).replace('T',' ')),(z,'Aktuelles Foto · '+str(last.get('measured_at','')).replace('T',' '))]:cells.append([im if im else '',Paragraph(esc(label),s['Caption'])])
   story+=[Paragraph('Fotovergleich',s['Heading3']),Table([cells],colWidths=[88*mm,88*mm],style=[('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#d9e1ea')),('PADDING',(0,0),(-1,-1),4)])]
 if not pts:story.append(Paragraph('Keine Rissmessstellen vorhanden.',s['BodyText']))
 story+=[Spacer(1,8*mm),Paragraph('4. Dokumentationshinweis',s['Heading1']),Paragraph('Dieser Bericht wurde aus den in Hausmonitor gespeicherten Messreihen, statistischen Kennwerten und Bilddateien erzeugt. Fehlende Werte werden mit einem Gedankenstrich dargestellt.',s['Small'])]
 doc.build(story,onFirstPage=footer,onLaterPages=footer);b.seek(0);return b
