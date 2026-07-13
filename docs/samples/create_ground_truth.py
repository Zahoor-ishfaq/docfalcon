"""Auto-generate ground truth JSON from iqama images using OCR + regex parsing. No LLM."""

import pathlib, sys, os, re, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from services.ocr import extract_text

FOLDER = pathlib.Path(__file__).parent / "iqama"


def parse_iqama_text(raw):
    """Extract fields from raw OCR text using Arabic label patterns."""
    fields = {
        "name_en": None, "name_ar": None, "iqama_number": None,
        "nationality": None, "profession": None, "expiry_date": None, "employer": None,
    }

    lines = [l.strip() for l in raw.replace("\n\n", "\n").split("\n") if l.strip()]

    # English name — all-caps line with latin letters
    for line in lines:
        if re.match(r'^[A-Z][A-Z\s\-\.]{4,}$', line.strip()):
            fields["name_en"] = line.strip()
            break

    # Arabic name — first Arabic-only line that isn't a label
    skip_words = {"هوية", "مقيم", "وزارة", "الداخلية", "المملكة", "العربية", "السعودية", "رقم", "النسخة", "يجب", "التحقق", "الرمز", "السريع", "قبل", "اعتماد", "التعامل", "الهوية"}
    for line in lines:
        clean = line.strip()
        if re.match(r'^[\u0600-\u06FF\s]+$', clean) and len(clean) > 5:
            words = set(clean.split())
            if not words.intersection(skip_words):
                fields["name_ar"] = clean
                break

    # 10-digit iqama number — first one after رقم الهوية
    full = " ".join(lines)
    iqama_match = re.search(r'(\d{10})', full)
    if iqama_match:
        fields["iqama_number"] = iqama_match.group(1)

    # Expiry — look for date pattern near الانتهاء
    # Try YYYY/MM/DD or Arabic numerals
    date_pattern = r'(\d{4}[/\-\.]\d{2}[/\-\.]\d{2})'
    expiry_section = re.split(r'الانتهاء', full)
    if len(expiry_section) > 1:
        date_match = re.search(date_pattern, expiry_section[1][:50])
        if date_match:
            fields["expiry_date"] = date_match.group(1).replace("/", "-")

    # If no Gregorian date found, try Arabic numerals ٠١٢٣٤٥٦٧٨٩
    if not fields["expiry_date"]:
        ar_digits = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        full_latin = full.translate(ar_digits)
        expiry_section = re.split(r'الانتهاء', full_latin + " " + full)
        if len(expiry_section) > 1:
            date_match = re.search(date_pattern, expiry_section[1][:50])
            if date_match:
                fields["expiry_date"] = date_match.group(1).replace("/", "-")

    # Nationality — after الجنسية
    nat_match = re.search(r'الجنسية[:\s]*([^\n:]+)', full)
    if nat_match:
        fields["nationality"] = nat_match.group(1).strip().split("  ")[0].strip()

    # Profession — after المهنة
    prof_match = re.search(r'المهنة[:\s]*([^\n:]+)', full)
    if prof_match:
        fields["profession"] = prof_match.group(1).strip().split("  ")[0].strip()

    # Employer — after اسم صاحب العمل
    emp_match = re.search(r'اسم صاحب العمل[:\s]*([^\n]+)', full)
    if emp_match:
        fields["employer"] = emp_match.group(1).strip()

    return fields


def main():
    pngs = sorted(FOLDER.glob("*.png"))
    if not pngs:
        print("No PNG files found in", FOLDER)
        return

    for img in pngs:
        json_path = img.with_suffix(".json")
        if json_path.exists():
            print(f"⏭ {img.name} — JSON exists, skipping")
            continue

        print(f"\n  Processing {img.name}...")
        raw = extract_text(img.read_bytes(), "image/png")
        fields = parse_iqama_text(raw)

        json_path.write_text(json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8")

        nulls = [k for k, v in fields.items() if v is None]
        print(f"  ✓ Saved {json_path.name}")
        if nulls:
            print(f"    ⚠ Could not parse: {', '.join(nulls)}")
        for k, v in fields.items():
            print(f"    {k}: {v}")


if __name__ == "__main__":
    main()