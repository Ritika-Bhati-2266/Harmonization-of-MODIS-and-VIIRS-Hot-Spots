from pathlib import Path
p = Path(r"D:\PROJECTS\Hackathon\Harmonization of MODIS and VIIRS Hot Spots\app.py")
# read raw bytes to see actual chars
b = p.read_bytes()
text = b.decode("utf-8")
# Replace the specific garbled sequences by their byte patterns interpreted as latin1/cp1252 mojibake remnants
# '0.25A�' likely '0.25Â°' or similar mis-decoded; easier to replace by context
fixes = {
    "0.25A\u00b0": "0.25\u00b0",
    "0.25\u00c2\u00b0": "0.25\u00b0",
    "0.25\u00b0?": "0.25\u00b0",
}
for k,v in fixes.items(): text = text.replace(k,v)
# brute: any occurrence of '0.25' followed by non-ascii before ' cell' or ' grid' or ' harmonized'
import re
text = re.sub(r'0.25[^\x00-\x7f]{1,3}(?= (?:cell|grid|harmonized))', '0.25\u00b0', text)
text = re.sub(r'VIIRS [^\x00-\x7f ]{1,3} 0.25\u00b0', 'VIIRS \u00b7 0.25\u00b0', text)
text = text.replace('\u00b7 0.25A\u00b0', '\u00b7 0.25\u00b0').replace('A\u00b0 0.25', '\u00b7 0.25')
# fix en dashes and symbols in text
text = text.replace(f'{chr(0xfffd)}?"', '\u2013').replace(f'{chr(0xfffd)}?\uFFFD', '\u2013')
text = re.sub(r'(\d{4})[^\x00-\x7f"\w]{1,3}(\{last_year\}|\d{4})', r'\1\u2013\2', text)
text = re.sub(r"(overlap_start['\)\}]+)[^\x00-\x7f\w]{1,3}(cal\.get\('overlap_end'\)|\{cal)", r'\1\u2013\2', text)
text = text.replace('confidence \ufffd%\ufffd 30', 'confidence \u2265 30').replace('confidence  30', 'confidence \u2265 30')
text = re.sub(r'0\.1[^\x00-\x7f\w]{1,3}3\.0', '0.1\u20133.0', text)
text = text.replace('VIIRS A\u00d7 ratio', 'VIIRS \u00d7 ratio').replace('VIIRS A ratio', 'VIIRS \u00d7 ratio').replace('VIIRS  ratio', 'VIIRS \u00d7 ratio')
text = re.sub(r'\s[^\x00-\x7f\w]{1,2}\sNASA Space Apps Challenge 2026\s[^\x00-\x7f\w]{1,2}\s', ' \u00b7 NASA Space Apps Challenge 2026 \u00b7 ', text)
text = re.sub(r'</strong>\s[^\x00-\x7f\w]{1,2}\sNASA Space Apps Challenge 2026\s[^\x00-\x7f\w]{1,2}', '</strong> \u00b7 NASA Space Apps Challenge 2026 \u00b7', text)
text = re.sub(r'NASA FIRMS\s[^\x00-\x7f\w]{1,2}\sHarmonized', 'NASA FIRMS \u00b7 Harmonized', text)
text = re.sub(r'0\.25\u00b0 grid\s[^\x00-\x7f\w]{1,2}<', '0.25\u00b0 grid \u00b7<', text)
text = re.sub(r'region_label\}\s[^\x00-\x7f\w]{1,2}\s\{first_year\}', 'region_label} \u00b7 {first_year}', text)
text = re.sub(r'last_year\}\s[^\x00-\x7f\w]{1,2}\s+overlap', 'last_year} \u00b7 overlap', text)
p.write_text(text, encoding='utf-8')
print('patched')
