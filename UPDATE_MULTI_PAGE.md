# UPDATE: Multi-Page Support Added

**Date:** November 2025  
**Changes:** Added support for multi-page documents (PDFs exported as multiple JPG pages)

---

## What Changed

### ✅ **Before (Problem)**
```bash
python3 tvode_automation.py --image page1.jpg --student "Desmond" --assignment "Week 4"
python3 tvode_automation.py --image page2.jpg --student "Desmond" --assignment "Week 4"
```
Result: 2 separate evaluations for same student

### ✅ **After (Fixed)**
```bash
python3 tvode_automation.py --image page1.jpg page2.jpg --student "Desmond" --assignment "Week 4"
```
Result: 1 combined evaluation with all pages merged

---

## Usage Examples

### Single Page (Still Works)
```bash
python3 tvode_automation.py \
  --image "student_work.jpg" \
  --student "Jayden" \
  --assignment "Week 3" \
  --output ./outputs
```

### Multi-Page (New)
```bash
python3 tvode_automation.py \
  --image "AIT week 4-1.jpg" "AIT week 4-2.jpg" \
  --student "Desmond" \
  --assignment "Week 4" \
  --output ./outputs
```

### With Wildcards (Easy)
```bash
python3 tvode_automation.py \
  --image AIT_week_4*.jpg \
  --student "Desmond" \
  --assignment "Week 4" \
  --output ./outputs
```

---

## How It Works

1. **Transcription Stage:**
   - Processes each page individually via Claude API
   - Combines all transcriptions with "\n\n" separator
   - Aggregates uncertainties from all pages
   - Uses worst handwriting quality across pages

2. **Evaluation Stage:**
   - Treats combined transcription as single document
   - Scores TVODE components across all pages
   - Generates one unified report card

3. **Output:**
   - Single transcript JSON with all pages
   - Single evaluation JSON
   - Single report card

---

## Cost Impact

**Per page:** ~$0.05-0.15 for transcription  
**2-page document:** ~$0.10-0.30 transcription + $0.10-0.30 evaluation = **$0.20-0.60 total**

Still cheaper than manual transcription!

---

## Technical Details

**Files Updated:**
- `tvode_transcriber.py` - Added `_transcribe_single_page()` method
- `tvode_automation.py` - Changed `--image` to accept multiple arguments

**Backward Compatible:** Single images still work exactly as before.

---

## Testing Checklist

Before using in production, test:
- [ ] Single page document
- [ ] 2-page document
- [ ] 3+ page document
- [ ] Mixed quality handwriting across pages
- [ ] Check combined transcription makes sense
- [ ] Verify scoring treats as one document

---

## Troubleshooting

**Problem:** "Unrecognized arguments"
**Fix:** Put filenames with spaces in quotes:
```bash
--image "page 1.jpg" "page 2.jpg"
```

**Problem:** PDF too large (>5MB)
**Fix:** Export to JPG first using Preview or online tool

**Problem:** Pages transcribed separately
**Fix:** Make sure you updated to the new version of the files

---

**Files to download from outputs directory:**
- [tvode_transcriber.py](computer:///mnt/user-data/outputs/tvode_transcriber.py) ← **Updated**
- [tvode_automation.py](computer:///mnt/user-data/outputs/tvode_automation.py) ← **Updated**
- tvode_evaluator.py (unchanged)

Replace your local copies with these updated versions.
