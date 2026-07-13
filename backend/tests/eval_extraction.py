"""E2.5 — Run OCR → LLM extraction on all samples, measure field-level accuracy."""

import pathlib, sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SAMPLES = pathlib.Path(__file__).resolve().parent.parent.parent / "docs" / "samples"

# Visa/contract still use generate scripts for ground truth
sys.path.insert(0, str(SAMPLES))
from generate_visa import RECORDS as VISA_RECORDS
from generate_contract import RECORDS as CONTRACT_RECORDS

from backend.services.ocr import extract_text
from backend.services.llm_client import extract


def load_iqama_pairs():
    """Dynamically load iqama PNGs + matching JSON ground truth."""
    folder = SAMPLES / "iqama"
    pairs = []
    for png in sorted(folder.glob("*.png")):
        json_path = png.with_suffix(".json")
        if json_path.exists():
            truth = json.loads(json_path.read_text(encoding="utf-8"))
            pairs.append((png, truth))
        else:
            print(f"  ⚠ Skipping {png.name} — no matching JSON")
    return pairs


def build_visa_truth(rec):
    name_en, name_ar, passport, visa_no, vtype_en, vtype_ar, sponsor_en, sponsor_ar, exp_g, exp_h, status = rec
    return {"name_en": name_en, "name_ar": name_ar, "passport_number": passport, "visa_number": visa_no, "visa_type": vtype_en, "expiry_date": exp_g, "sponsor": sponsor_en}


def build_contract_truth(rec):
    name_en, name_ar, emp_en, emp_ar, pos_en, pos_ar, start, end, salary, ctr_no, status = rec
    return {"employee_name": name_en, "employer": emp_en, "position": pos_en, "start_date": start, "end_date": end, "salary": f"{salary} SAR"}


# Arabic ↔ English equivalents
BILINGUAL = {
    "مصري": "egyptian", "باكستاني": "pakistani", "هندي": "indian",
    "أردني": "jordanian", "سوداني": "sudanese", "بنغلاديشي": "bangladeshi",
    "لبناني": "lebanese", "يمني": "yemeni",
    "مهندس برمجيات": "software engineer", "محاسب": "accountant",
    "مهندس مدني": "civil engineer", "معلم": "teacher", "ممرض": "nurse",
    "مهندس كهربائي": "electrical engineer", "مدير تسويق": "marketing manager",
    "محلل بيانات": "data analyst", "صيدلي": "pharmacist", "مصمم جرافيك": "graphic designer",
    "سابك": "sabic",
    "شركة الراجحي للتجارة": "al-rajhi trading company",
    "شركة دار الأركان": "dar al arkan company",
}

# Persian ی → Arabic ي normalization
def _normalize_ar(text):
    return text.replace("ی", "ي").replace("ک", "ك")


def fuzzy_match(expected, actual):
    if expected is None:
        return actual is None
    if actual is None:
        return False
    e = _normalize_ar(expected.lower().strip())
    a = _normalize_ar(actual.lower().strip())
    if e in a or a in e:
        return True
    for ar, en in BILINGUAL.items():
        ar_n = _normalize_ar(ar.lower())
        if (e == ar_n and en in a) or (e == en and ar_n in a):
            return True
        if (a == ar_n and en in e) or (a == en and ar_n in e):
            return True
    return False


def eval_doc(filepath, doc_type, truth, content_type):
    raw_bytes = filepath.read_bytes()
    ocr_text = extract_text(raw_bytes, content_type)
    result = extract(ocr_text, doc_type)

    hits, total, details = 0, 0, []
    for field, expected in truth.items():
        total += 1
        actual = result.get(field)
        if fuzzy_match(expected, actual):
            hits += 1
        else:
            details.append(f"  ✗ {field}: expected={expected!r} got={actual!r}")
    return hits, total, details


def main():
    grand_hits, grand_total = 0, 0
    field_stats = {}

    # --- IQAMA (dynamic) ---
    iqama_pairs = load_iqama_pairs()
    print(f"\n{'='*60}")
    print(f"  IQAMA ({len(iqama_pairs)} docs)")
    print(f"{'='*60}")

    for filepath, truth in iqama_pairs:
        print(f"\n  {filepath.name}")
        try:
            hits, total, details = eval_doc(filepath, "iqama", truth, "image/png")
            grand_hits += hits
            grand_total += total
            pct = (hits / total * 100) if total else 0
            print(f"  {hits}/{total} fields correct ({pct:.0f}%)")
            for d in details:
                print(d)
            for field in truth:
                if field not in field_stats:
                    field_stats[field] = [0, 0]
                field_stats[field][1] += 1
            # Re-extract for per-field stats
            result = extract(extract_text(filepath.read_bytes(), "image/png"), "iqama")
            for field, expected in truth.items():
                if fuzzy_match(expected, result.get(field)):
                    field_stats[field][0] += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            grand_total += len(truth)

    # --- VISA (from generate script) ---
    print(f"\n{'='*60}")
    print(f"  VISA ({len(VISA_RECORDS)} docs)")
    print(f"{'='*60}")

    for i, rec in enumerate(VISA_RECORDS, 1):
        truth = build_visa_truth(rec)
        filepath = SAMPLES / "visa" / f"visa_{i:02d}.png"
        print(f"\n  {filepath.name}")
        try:
            hits, total, details = eval_doc(filepath, "visa", truth, "image/png")
            grand_hits += hits
            grand_total += total
            pct = (hits / total * 100) if total else 0
            print(f"  {hits}/{total} fields correct ({pct:.0f}%)")
            for d in details:
                print(d)
            for field in truth:
                if field not in field_stats:
                    field_stats[field] = [0, 0]
                field_stats[field][1] += 1
            result = extract(extract_text(filepath.read_bytes(), "image/png"), "visa")
            for field, expected in truth.items():
                if fuzzy_match(expected, result.get(field)):
                    field_stats[field][0] += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            grand_total += len(truth)

    # --- CONTRACT (from generate script) ---
    print(f"\n{'='*60}")
    print(f"  CONTRACT ({len(CONTRACT_RECORDS)} docs)")
    print(f"{'='*60}")

    for i, rec in enumerate(CONTRACT_RECORDS, 1):
        truth = build_contract_truth(rec)
        filepath = SAMPLES / "contract" / f"contract_{i:02d}.pdf"
        print(f"\n  {filepath.name}")
        try:
            hits, total, details = eval_doc(filepath, "contract", truth, "application/pdf")
            grand_hits += hits
            grand_total += total
            pct = (hits / total * 100) if total else 0
            print(f"  {hits}/{total} fields correct ({pct:.0f}%)")
            for d in details:
                print(d)
            for field in truth:
                if field not in field_stats:
                    field_stats[field] = [0, 0]
                field_stats[field][1] += 1
            result = extract(extract_text(filepath.read_bytes(), "application/pdf"), "contract")
            for field, expected in truth.items():
                if fuzzy_match(expected, result.get(field)):
                    field_stats[field][0] += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            grand_total += len(truth)

    # --- SUMMARY ---
    overall = (grand_hits / grand_total * 100) if grand_total else 0
    print(f"\n{'='*60}")
    print(f"  OVERALL: {grand_hits}/{grand_total} fields ({overall:.1f}%)")
    print(f"  TARGET:  ≥90%  {'✅ PASS' if overall >= 90 else '❌ FAIL'}")
    print(f"{'='*60}")

    print(f"\n  PER-FIELD BREAKDOWN:")
    for field, (h, t) in sorted(field_stats.items()):
        pct = (h / t * 100) if t else 0
        print(f"    {field:20s}  {h}/{t}  ({pct:.0f}%)")


if __name__ == "__main__":
    main()
