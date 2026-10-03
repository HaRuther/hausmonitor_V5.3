from pathlib import Path
p=Path("app/main.py");s=p.read_text(encoding="utf-8")
needle=",'sd_sw':c['stats']['SW']['sd']"
insert=",'anb_delta':c['stats']['anb_sw']['delta'],'anb_se':c['stats']['anb_sw']['se'],'anb_low':c['stats']['anb_sw']['delta']-c['stats']['anb_sw']['se'] if c['stats']['anb_sw']['delta'] is not None and c['stats']['anb_sw']['se'] is not None else None,'anb_high':c['stats']['anb_sw']['delta']+c['stats']['anb_sw']['se'] if c['stats']['anb_sw']['delta'] is not None and c['stats']['anb_sw']['se'] is not None else None"
if needle not in s:raise SystemExit("Einfügeposition nicht gefunden")
p.write_text(s.replace(needle,insert+needle,1),encoding="utf-8")
