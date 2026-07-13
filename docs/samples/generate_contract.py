"""Generate 5 fake Saudi employment contract PDFs via Playwright. Run once, commit PDFs, delete script."""

import asyncio, pathlib
from playwright.async_api import async_playwright

OUT = pathlib.Path(__file__).parent / "contract"
OUT.mkdir(parents=True, exist_ok=True)

RECORDS = [
    # (name_en, name_ar, employer_en, employer_ar, position_en, position_ar, start, end, salary_sar, contract_no, status)
    ("Ahmed Hassan Al-Farsi",  "أحمد حسن الفارسي",  "Al-Rajhi Corporation",  "شركة الراجحي",    "Software Engineer",    "مهندس برمجيات",  "2022-01-15", "2024-12-31", "12,000", "CTR-2022-0451", "expired"),
    ("Mohammed Raza Khan",     "محمد رضا خان",       "Saudi Oger Ltd",        "سعودي أوجيه",     "Senior Accountant",    "محاسب أول",      "2023-06-01", "2025-08-31", "15,500", "CTR-2023-0782", "expiring"),
    ("Tariq Ismail Siddiqui",  "طارق إسماعيل صديقي", "Binladin Group",        "مجموعة بن لادن",  "Civil Engineer",       "مهندس مدني",     "2023-09-15", "2025-09-14", "14,000", "CTR-2023-1034", "expiring"),
    ("Khalid Ibrahim Malik",   "خالد إبراهيم مالك",  "SABIC",                 "سابك",            "Electrical Engineer",  "مهندس كهربائي",  "2024-03-01", "2026-09-30", "16,000", "CTR-2024-0198", "valid"),
    ("Bilal Saeed Rahman",     "بلال سعيد رحمن",     "Al-Marai Company",      "شركة المراعي",    "Data Analyst",         "محلل بيانات",    "2024-07-01", "2027-06-30", "13,500", "CTR-2024-0567", "valid"),
]

def html(r):
    name_en, name_ar, emp_en, emp_ar, pos_en, pos_ar, start, end, salary, ctr_no, status = r
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+Arabic:wght@400;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:794px; padding:60px; font-family:'Inter','Noto Sans Arabic',sans-serif; background:#fff; color:#1a1a1a; }}
  .header {{ text-align:center; margin-bottom:40px; border-bottom:3px solid #1A237E; padding-bottom:20px; }}
  .title-ar {{ font-size:24px; font-weight:700; color:#1A237E; direction:rtl; margin-bottom:4px; font-family:'Noto Sans Arabic',sans-serif; }}
  .title-en {{ font-size:20px; font-weight:700; color:#1A237E; margin-bottom:8px; }}
  .contract-no {{ font-size:13px; color:#666; }}
  .section {{ margin-bottom:24px; }}
  .section-title {{ font-size:14px; font-weight:700; color:#1A237E; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; border-bottom:1px solid #C5CAE9; padding-bottom:4px; }}
  table {{ width:100%; border-collapse:collapse; }}
  td {{ padding:8px 12px; font-size:14px; vertical-align:top; }}
  td.label {{ font-weight:600; color:#555; width:35%; }}
  td.value {{ color:#1a1a1a; font-weight:500; }}
  td.label-ar {{ font-weight:600; color:#555; text-align:right; direction:rtl; font-family:'Noto Sans Arabic',sans-serif; }}
  td.value-ar {{ text-align:right; direction:rtl; font-family:'Noto Sans Arabic',sans-serif; font-weight:500; }}
  .clause {{ font-size:13px; line-height:1.7; color:#333; margin-bottom:10px; }}
  .clause-num {{ font-weight:700; color:#1A237E; }}
  .signatures {{ display:flex; justify-content:space-between; margin-top:50px; padding-top:20px; border-top:1px solid #ddd; }}
  .sig-block {{ text-align:center; width:40%; }}
  .sig-line {{ border-top:1px solid #333; margin-top:60px; padding-top:8px; font-size:13px; color:#555; }}
  .stamp {{ margin-top:16px; width:100px; height:100px; border:2px dashed #C5CAE9; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; color:#9FA8DA; font-size:11px; }}
</style></head>
<body>
  <div class="header">
    <div class="title-ar">عقد عمل</div>
    <div class="title-en">EMPLOYMENT CONTRACT</div>
    <div class="contract-no">{ctr_no}</div>
  </div>

  <div class="section">
    <div class="section-title">Parties / الأطراف</div>
    <table>
      <tr><td class="label">Employer</td><td class="value">{emp_en}</td><td class="value-ar">{emp_ar}</td><td class="label-ar">صاحب العمل</td></tr>
      <tr><td class="label">Employee</td><td class="value">{name_en}</td><td class="value-ar">{name_ar}</td><td class="label-ar">الموظف</td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">Employment Details / تفاصيل العمل</div>
    <table>
      <tr><td class="label">Position</td><td class="value">{pos_en}</td><td class="value-ar">{pos_ar}</td><td class="label-ar">المسمى الوظيفي</td></tr>
      <tr><td class="label">Start Date</td><td class="value">{start}</td><td class="value-ar">{start}</td><td class="label-ar">تاريخ البدء</td></tr>
      <tr><td class="label">End Date</td><td class="value">{end}</td><td class="value-ar">{end}</td><td class="label-ar">تاريخ الانتهاء</td></tr>
      <tr><td class="label">Monthly Salary</td><td class="value">{salary} SAR</td><td class="value-ar">ريال {salary}</td><td class="label-ar">الراتب الشهري</td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">Terms & Conditions / الشروط والأحكام</div>
    <div class="clause"><span class="clause-num">1.</span> The Employee shall perform duties as assigned by the Employer in accordance with Saudi Labor Law.</div>
    <div class="clause"><span class="clause-num">2.</span> Working hours shall not exceed 8 hours per day or 48 hours per week, as per Article 98 of the Saudi Labor Law.</div>
    <div class="clause"><span class="clause-num">3.</span> The Employee is entitled to 21 days of annual leave after completing one year of service, increasing to 30 days after five years.</div>
    <div class="clause"><span class="clause-num">4.</span> Either party may terminate this contract with 30 days written notice during the probation period (90 days).</div>
    <div class="clause"><span class="clause-num">5.</span> End-of-service benefits shall be calculated in accordance with Articles 84-86 of the Saudi Labor Law.</div>
    <div class="clause"><span class="clause-num">6.</span> The Employer shall provide medical insurance coverage as required by the Cooperative Health Insurance Law.</div>
  </div>

  <div class="signatures">
    <div class="sig-block">
      <div class="sig-line">Employer Signature / توقيع صاحب العمل</div>
      <div class="stamp">COMPANY SEAL</div>
    </div>
    <div class="sig-block">
      <div class="sig-line">Employee Signature / توقيع الموظف</div>
    </div>
  </div>
</body></html>"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for i, rec in enumerate(RECORDS, 1):
            await page.set_content(html(rec))
            await page.wait_for_load_state("networkidle")
            path = OUT / f"contract_{i:02d}.pdf"
            await page.pdf(path=str(path), format="A4", print_background=True)
            print(f"✓ {path.name}")
        await browser.close()

asyncio.run(main())