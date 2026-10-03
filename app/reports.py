from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image as RImage

def f(v,n=3):return '–' if v is None else f'{v:.{n}f}'
def tab(rows,widths=None):
 t=Table(rows,repeatRows=1,colWidths=widths);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17365d')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.25,colors.grey),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP')]));return t
def make_report(cs,pts,assessment,level_dir,crack_dir,year=None):
 if year:cs=[c for c in cs if c['measured_at'].startswith(str(year))];pts=[dict(p,measurements=[m for m in p['measurements'] if m['measured_at'].startswith(str(year))]) for p in pts]
 b=BytesIO();doc=SimpleDocTemplate(b,pagesize=A4,rightMargin=12*mm,leftMargin=12*mm,topMargin=12*mm,bottomMargin=12*mm);s=getSampleStyleSheet();story=[Paragraph(f"Hausmonitor Bericht{' '+str(year) if year else ''}",s['Title']),Paragraph(assessment,s['BodyText']),Spacer(1,5*mm),Paragraph('Nivellement',s['Heading2'])]
 rows=[['Datum','Haus','Δ','SE','SNR','Terrasse','GW','Luft']]
 for c in cs:rows.append([c['measured_at'].replace('T',' '),f(c['stats']['house']['value']),f(c['stats']['house']['delta']),f(c['stats']['house']['se']),f(c['stats']['house']['snr'],2),f(c['stats']['terrace']['value']),f(c['groundwater']),f(c['air_temp'],1)])
 story.append(tab(rows,[32*mm,20*mm,18*mm,18*mm,17*mm,22*mm,18*mm,17*mm]))
 story+=[PageBreak(),Paragraph('Rissmonitoring',s['Heading2'])]
 for p in pts:
  story+=[Paragraph(p['name'],s['Heading3']),Paragraph(f"Ort: {p['location'] or '–'} · Art: {p['crack_type'] or '–'} · Status: {p['status']} · Änderung: {f(p['delta'])} {p['unit']}",s['BodyText'])]
  rr=[['Datum','Temp.','Wert','Δ','Notiz']]
  for m in p['measurements']:rr.append([m['measured_at'].replace('T',' '),f(m['air_temp'],1),f(m['value']),f(m['delta']),m['notes'] or ''])
  story.append(tab(rr,[40*mm,20*mm,22*mm,22*mm,70*mm]))
  for m in p['measurements']:
   if m['photo_filename'] and (crack_dir/m['photo_filename']).exists():story+=[Spacer(1,2*mm),RImage(str(crack_dir/m['photo_filename']),width=72*mm,height=54*mm,kind='proportional')]
  story.append(Spacer(1,4*mm))
 story+=[Spacer(1,4*mm),Paragraph('Hinweis: Statistische Bewertungen unterstützen das Monitoring, ersetzen aber keine bautechnische oder geotechnische Begutachtung.',s['BodyText'])]
 doc.build(story);b.seek(0);return b
