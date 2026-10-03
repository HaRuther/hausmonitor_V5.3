from pathlib import Path
p=Path("app/reports.py");s=p.read_text(encoding="utf-8")
start=s.index("def level_chart(cs):");end=s.index("def sd_chart(cs):")
new="""def difference_chart(cs,stats_key,title,line_label,band_color,line_color):
 r=[]
 for c in cs:
  d=dt(c.get('measured_at'));v=c.get('stats',{}).get(stats_key,{});delta=v.get('delta');se=v.get('se')
  if d and delta is not None:r.append((d,float(delta),float(se) if se is not None else 0))
 if not r:return None
 r.sort();x=[z[0] for z in r];y=[z[1] for z in r];lo=[z[1]-z[2] for z in r];hi=[z[1]+z[2] for z in r]
 fig,ax=plt.subplots(figsize=(8.6,3.6));ax.fill_between(x,lo,hi,color=band_color,alpha=.35,label='± kombinierter Standardfehler');ax.plot(x,y,color=line_color,lw=2.2,marker='o',label=line_label);ax.axhline(0,color='#59636e',lw=.9);ax.set_title(title);ax.set_ylabel('Differenz [mm]');axis(ax);ax.legend(frameon=False,fontsize=8);fig.tight_layout();return fig_image(fig)
def level_chart(cs):return difference_chart(cs,'house','Differenz SO-SW mit Fehlerband','SO-SW','#7fc3ff',ACCENT)
def anb_sw_chart(cs):return difference_chart(cs,'anb_sw','Differenz ANB-SW mit Fehlerband','ANB-SW','#86efac',GREEN)
"""
s=s[:start]+new+s[end:]
old="for title,ch in [('2.1 Änderung mit Fehlerband',level_chart(cs)),('2.2 Messstreuung',sd_chart(cs))]:"
newlist="for title,ch in [('2.1 Differenz SO-SW mit Fehlerband',level_chart(cs)),('2.2 Differenz ANB-SW mit Fehlerband',anb_sw_chart(cs)),('2.3 Messstreuung',sd_chart(cs))]:"
if old not in s:raise SystemExit("Diagrammliste nicht gefunden")
p.write_text(s.replace(old,newlist,1),encoding="utf-8")
