"""Generate 5 fake Saudi visa PNGs via Playwright. Run once, commit images, delete script."""

import asyncio, pathlib
from playwright.async_api import async_playwright

OUT = pathlib.Path(__file__).parent / "visa"
OUT.mkdir(parents=True, exist_ok=True)

RECORDS = [
    # (name_en, name_ar, passport_no, visa_no, visa_type_en, visa_type_ar, sponsor_en, sponsor_ar, expiry_greg, expiry_hijri, status)
    ("Ahmed Hassan Al-Farsi",  "أحمد حسن الفارسي",   "A12984567", "4481029301", "Work Visa",      "تأشيرة عمل",    "Al-Rajhi Corp",       "شركة الراجحي",     "2025-03-15", "1446-09-15", "expired"),
    ("Mohammed Raza Khan",     "محمد رضا خان",        "B93847261", "4592038412", "Work Visa",      "تأشيرة عمل",    "Saudi Oger Ltd",      "سعودي أوجيه",      "2025-08-20", "1447-02-25", "expiring"),
    ("Tariq Ismail Siddiqui",  "طارق إسماعيل صديقي",  "C74629183", "4603947523", "Business Visa",  "تأشيرة تجارية", "Binladin Group",      "مجموعة بن لادن",   "2025-09-10", "1447-03-16", "expiring"),
    ("Khalid Ibrahim Malik",   "خالد إبراهيم مالك",   "D58371946", "4714856634", "Work Visa",      "تأشيرة عمل",    "SABIC",               "سابك",             "2026-06-30", "1448-01-06", "valid"),
    ("Bilal Saeed Rahman",     "بلال سعيد رحمن",      "E29184750", "4825967745", "Family Visa",    "تأشيرة عائلية", "Al-Marai Company",    "شركة المراعي",     "2027-01-15", "1448-07-26", "valid"),
]

def status_color(s):
    return {"expired": "#DC2626", "expiring": "#F59E0B", "valid": "#16A34A"}[s]

def html(r):
    name_en, name_ar, passport, visa_no, vtype_en, vtype_ar, sponsor_en, sponsor_ar, exp_g, exp_h, status = r
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+Arabic:wght@400;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:860px; height:540px; font-family:'Inter','Noto Sans Arabic',sans-serif; background:#fff; }}
  .card {{ width:860px; height:540px; border:2px solid #1A237E; border-radius:16px; overflow:hidden; position:relative; }}
  .header {{ background:linear-gradient(135deg,#1A237E,#283593); height:80px; display:flex; align-items:center; justify-content:space-between; padding:0 30px; }}
  .header-en {{ color:#fff; font-size:18px; font-weight:700; letter-spacing:1px; }}
  .header-ar {{ color:#fff; font-size:20px; font-weight:700; direction:rtl; }}
  .body {{ display:flex; padding:20px 30px; gap:24px; height:380px; }}
  .photo {{ width:160px; height:200px; background:#E8EAF6; border:2px solid #9FA8DA; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#7986CB; font-size:13px; flex-shrink:0; }}
  .fields {{ flex:1; display:grid; grid-template-columns:1fr 1fr; gap:8px 32px; align-content:start; }}
  .field {{ display:flex; flex-direction:column; gap:2px; }}
  .field.rtl {{ direction:rtl; text-align:right; }}
  .label {{ font-size:11px; color:#888; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }}
  .label-ar {{ font-size:12px; color:#888; font-weight:600; }}
  .value {{ font-size:16px; font-weight:600; color:#1a1a1a; }}
  .value-ar {{ font-size:17px; font-weight:600; color:#1a1a1a; font-family:'Noto Sans Arabic',sans-serif; }}
  .footer {{ position:absolute; bottom:0; width:100%; height:60px; background:#E8EAF6; display:flex; align-items:center; justify-content:space-between; padding:0 30px; border-top:1px solid #C5CAE9; }}
  .visa-big {{ font-size:22px; font-weight:700; color:#1A237E; letter-spacing:2px; }}
  .status {{ padding:6px 16px; border-radius:20px; color:#fff; font-weight:700; font-size:13px; background:{status_color(status)}; }}
</style></head>
<body><div class="card">
  <div class="header">
    <span class="header-en">KINGDOM OF SAUDI ARABIA — ENTRY VISA</span>
    <span class="header-ar">المملكة العربية السعودية — تأشيرة دخول</span>
  </div>
  <div class="body">
    <div class="photo">PHOTO</div>
    <div class="fields">
      <div class="field"><span class="label">Full Name</span><span class="value">{name_en}</span></div>
      <div class="field rtl"><span class="label-ar">الاسم الكامل</span><span class="value-ar">{name_ar}</span></div>

      <div class="field"><span class="label">Passport Number</span><span class="value">{passport}</span></div>
      <div class="field rtl"><span class="label-ar">رقم جواز السفر</span><span class="value-ar">{passport}</span></div>

      <div class="field"><span class="label">Visa Number</span><span class="value">{visa_no}</span></div>
      <div class="field rtl"><span class="label-ar">رقم التأشيرة</span><span class="value-ar">{visa_no}</span></div>

      <div class="field"><span class="label">Visa Type</span><span class="value">{vtype_en}</span></div>
      <div class="field rtl"><span class="label-ar">نوع التأشيرة</span><span class="value-ar">{vtype_ar}</span></div>

      <div class="field"><span class="label">Sponsor</span><span class="value">{sponsor_en}</span></div>
      <div class="field rtl"><span class="label-ar">الكفيل</span><span class="value-ar">{sponsor_ar}</span></div>

      <div class="field"><span class="label">Expiry (Gregorian)</span><span class="value">{exp_g}</span></div>
      <div class="field rtl"><span class="label-ar">تاريخ الانتهاء (هجري)</span><span class="value-ar">{exp_h}</span></div>
    </div>
  </div>
  <div class="footer">
    <span class="visa-big">{visa_no}</span>
    <span class="status">{status.upper()}</span>
  </div>
</div></body></html>"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 860, "height": 540})
        for i, rec in enumerate(RECORDS, 1):
            await page.set_content(html(rec))
            await page.wait_for_load_state("networkidle")
            path = OUT / f"visa_{i:02d}.png"
            await page.screenshot(path=str(path))
            print(f"✓ {path.name}")
        await browser.close()

asyncio.run(main())