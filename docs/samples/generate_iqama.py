"""Generate 10 fake Iqama PNGs — Playwright HTML overlay on background template."""

import asyncio, pathlib, json, base64

OUT = pathlib.Path(__file__).parent / "iqama"
OUT.mkdir(parents=True, exist_ok=True)
BG = pathlib.Path(__file__).parent / "iqama_background.png"

RECORDS = [
    # (name_en, name_ar, iqama_no, dob, nationality, profession, expiry, employer, birthplace, employer_id)
    ("AHMED HASSAN AL-FARSI",   "أحمد حسن الفارسي",     "2381029456", "1988/03/15", "مصري",      "مهندس برمجيات",  "2025/02/10", "شركة الراجحي للتجارة",    "القاهرة",    "7052930224"),
    ("MOHAMMED RAZA KHAN",      "محمد رضا خان",          "2492038571", "1991/07/22", "باكستاني",   "محاسب",          "2025/06/30", "مؤسسة راشد العليان",      "لاهور",      "7103847291"),
    ("TARIQ ISMAIL SIDDIQUI",   "طارق إسماعيل صديقي",   "2103947628", "1985/11/03", "هندي",       "مهندس مدني",     "2025/07/25", "مجموعة بن لادن",          "مومباي",     "7214958302"),
    ("YUSUF ALI MOSTAFA",       "يوسف علي مصطفى",        "2274856139", "1993/01/19", "أردني",      "معلم",           "2025/08/15", "شركة المعرفة للتعليم",    "عمّان",      "7326069413"),
    ("OMAR ABDULAZIZ NASSER",   "عمر عبدالعزيز ناصر",   "2385920174", "1990/05/08", "سوداني",     "ممرض",           "2025/09/01", "مستشفى الحمادي",          "الخرطوم",    "7437170524"),
    ("KHALID IBRAHIM MALIK",    "خالد إبراهيم مالك",    "2596031482", "1987/09/27", "بنغلاديشي",  "مهندس كهربائي",  "2026/04/20", "سابك",                    "دكا",        "7548281635"),
    ("FAISAL NAWAZ CHAUDHRY",   "فيصل نواز تشودري",     "2407168295", "1994/12/01", "باكستاني",   "مدير تسويق",     "2026/08/15", "شركة الاتصالات السعودية", "إسلام آباد", "7659392746"),
    ("BILAL SAEED RAHMAN",      "بلال سعيد رحمن",       "2718203946", "1989/04/14", "هندي",       "محلل بيانات",    "2026/11/30", "شركة المراعي",            "نيودلهي",    "7760403857"),
    ("HASSAN JAMAL AL-BAKRI",   "حسن جمال البكري",      "2829314057", "1986/08/30", "يمني",       "صيدلي",          "2027/03/10", "صيدليات الدواء",          "صنعاء",      "7871514968"),
    ("SAMIR ELIAS HADDAD",      "سمير إلياس حداد",      "2930425168", "1992/02/25", "لبناني",     "مصمم جرافيك",    "2027/07/22", "شركة دار الأركان",        "بيروت",      "7982625079"),
]


def build_html(rec, bg_base64):
    name_en, name_ar, iqama, dob, nat, prof, expiry, employer, birthplace, emp_id = rec
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:1012px; height:638px; font-family:'Noto Sans Arabic',sans-serif; }}
  .card {{ width:1012px; height:638px; position:relative; background:url('data:image/png;base64,{bg_base64}') no-repeat center/cover; }}
  .name-ar {{ position:absolute; top:120px; right:100px; font-size:32px; font-weight:700; color:#222; direction:rtl; }}
  .name-en {{ position:absolute; top:168px; left:390px; font-size:26px; font-weight:700; color:#222; letter-spacing:1px; }}

  .field {{ position:absolute; direction:rtl; text-align:right; background:rgba(248,246,238,0.85); padding:1px 6px; }}
  .label {{ font-size:18px; font-weight:700; color:#8c7b18; }}
  .value {{ font-size:18px; font-weight:600; color:#222; margin-right:8px; }}

  .f-id    {{ top:215px; right:80px; }}
  .f-exp   {{ top:215px; right:440px; }}
  .f-dob   {{ top:260px; right:80px; }}
  .f-bp    {{ top:260px; right:440px; }}
  .f-nat   {{ top:305px; right:80px; }}
  .f-rel   {{ top:305px; right:440px; }}
  .f-prof  {{ top:350px; right:80px; }}
  .f-eid   {{ top:400px; right:80px; }}
  .f-issue {{ top:445px; right:80px; }}
  .f-work  {{ top:490px; right:80px; }}
  .f-emp   {{ top:535px; right:80px; }}
</style></head>
<body><div class="card">
  <div class="name-ar">{name_ar}</div>
  <div class="name-en">{name_en}</div>

  <div class="field f-id"><span class="label">رقم الهوية:</span> <span class="value">{iqama}</span></div>
  <div class="field f-exp"><span class="label">تاريخ الانتهاء:</span> <span class="value">{expiry}</span></div>

  <div class="field f-dob"><span class="label">تاريخ الميلاد:</span> <span class="value">{dob}</span></div>
  <div class="field f-bp"><span class="label">مكان الميلاد:</span> <span class="value">{birthplace}</span></div>

  <div class="field f-nat"><span class="label">الجنسية:</span> <span class="value">{nat}</span></div>
  <div class="field f-rel"><span class="label">الديانة:</span> <span class="value">الإسلام</span></div>

  <div class="field f-prof"><span class="label">المهنة:</span> <span class="value">{prof}</span></div>

  <div class="field f-eid"><span class="label">هوية صاحب العمل:</span> <span class="value">{emp_id}</span></div>

  <div class="field f-issue"><span class="label">مكان الإصدار:</span> <span class="value">المنطقة الشرقية</span></div>

  <div class="field f-work"><span class="label">مكان العمل:</span> <span class="value">الرياض</span></div>

  <div class="field f-emp"><span class="label">اسم صاحب العمل:</span> <span class="value">{employer}</span></div>
</div></body></html>"""


def save_ground_truth(rec, path):
    name_en, name_ar, iqama, dob, nat, prof, expiry, employer, birthplace, emp_id = rec
    truth = {
        "name_en": name_en,
        "name_ar": name_ar,
        "iqama_number": iqama,
        "nationality": nat,
        "profession": prof,
        "expiry_date": expiry.replace("/", "-"),
        "employer": employer,
    }
    path.with_suffix(".json").write_text(
        json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )


async def main():
    from playwright.async_api import async_playwright

    if not BG.exists():
        print(f"✗ Background not found: {BG}")
        return

    bg_b64 = base64.b64encode(BG.read_bytes()).decode()

    # Clean old files
    for old in OUT.glob("iqama_*.png"):
        old.unlink()
    for old in OUT.glob("iqama_*.json"):
        old.unlink()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1012, "height": 638})

        for i, rec in enumerate(RECORDS, 1):
            await page.set_content(build_html(rec, bg_b64))
            await page.wait_for_load_state("networkidle")
            path = OUT / f"iqama_{i:02d}.png"
            await page.screenshot(path=str(path))
            save_ground_truth(rec, path)
            print(f"✓ {path.name} + {path.stem}.json")

        await browser.close()

    print(f"\nGenerated {len(RECORDS)} iqamas with ground truth.")


asyncio.run(main())