from pathlib import Path
p = Path(r"D:\PROJECTS\Hackathon\Harmonization of MODIS and VIIRS Hot Spots\app.py")
s = p.read_text(encoding='utf-8')
replacements = [
    ('0.25\uFFFD', '0.25\u00B0'),  # 0.25� -> 0.25°
    ('first_year}\ufffd?"{last_year}', 'first_year}\u2013{last_year}'),
    ('first_year}\ufffd?\ufffd{last_year}', 'first_year}\u2013{last_year}'),
    ('cal.get(\'overlap_start\')}\ufffd?"{cal.get(\'overlap_end\')}', "cal.get('overlap_start')}\u2013{cal.get('overlap_end')}"),
    ('cal.get(\'overlap_start\')}\ufffd?\ufffd{cal.get(\'overlap_end\')}', "cal.get('overlap_start')}\u2013{cal.get('overlap_end')}"),
    ('confidence \ufffd%\ufffd 30', 'confidence \u2265 30'),
    ('0.1\ufffd?"3.0', '0.1\u20133.0'),
    ('0.1\ufffd?\ufffd3.0', '0.1\u20133.0'),
    ('VIIRS A\u00d7 ratio', 'VIIRS \u00d7 ratio'),
    ('VIIRS A- ratio', 'VIIRS \u00d7 ratio'),
    ('\ufffd NASA Space Apps Challenge 2026 \ufffd', '\u00b7 NASA Space Apps Challenge 2026 \u00b7'),
    ('NASA FIRMS \ufffd Harmonized to a 0.25\u00b0 grid \ufffd', 'NASA FIRMS \u00b7 Harmonized to a 0.25\u00b0 grid \u00b7'),
    ('Bundled extract: {region_label} \ufffd {first_year}\u2013{last_year} \ufffd', 'Bundled extract: {region_label} \u00b7 {first_year}\u2013{last_year} \u00b7'),
]
for a,b in replacements:
    s = s.replace(a,b)
# generic fallbacks
s = s.replace('\ufffd', '') # remove remaining replacement chars if any risky? better targeted
p.write_text(s, encoding='utf-8')
print('written')
