# TVODE Diagnostic Automation System

**Version:** 2.0  
**Date:** November 2025

Complete automation for transcribing, evaluating, and reporting on student TVODE writing.

---

## Architecture

The system is now split into modular CLI scripts:

✅ **transcribe.py** - Stage 1: Image → JSON transcript  
✅ **evaluate.py** - Stage 2: Transcript → Evaluation  
✅ **automate.py** - Full pipeline wrapper (transcribe + evaluate)

**New Structure:**
- `src/transcriber/` - Transcription engine
- `src/evaluators/` - Evaluator registry (tvode, future evaluators)
- `src/evaluators/tvode/` - TVODE rubric implementation

---

## Quick Start

### Full Pipeline (Recommended)

```bash
python automate.py \
  --image student_work.jpg \
  --student "Coden" \
  --assignment "Week 4" \
  --evaluator tvode
```

### Step-by-Step (For Review)

```bash
# Step 1: Transcribe
python transcribe.py \
  --image student_work.jpg \
  --student "Coden" \
  --assignment "Week 4"

# Step 2: Review transcript if needed
# Edit outputs/transcripts/Coden_Week_4_transcript.json

# Step 3: Evaluate
python evaluate.py \
  --transcript outputs/transcripts/Coden_Week_4_transcript.json \
  --evaluator tvode
```

### With Kernel Context

```bash
python automate.py \
  --image student_work.jpg \
  --student "Coden" \
  --assignment "Week 4" \
  --evaluator tvode \
  --kernel kernels/The_Giver_kernel_v3_4.json \
  --reasoning reasoning/The_Giver_ReasoningDoc_v3.3.md
```

---

## Pipeline Stages

### Stage 1: Transcription

**What it does:**
- Sends image to Claude API
- Returns structured JSON with uncertainties
- Calculates accuracy score (0-100%)
- Flags sections needing review

**Output:**
```
outputs/transcripts/Coden_Week_4_transcript.json
```

**Auto-accept criteria:**
- No uncertainties AND
- Clear/moderate handwriting AND
- Accuracy ≥ 90%

---

### Stage 2: Review

**Targeted review** - only shows flagged sections:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REVIEW NEEDED: 1 uncertain section
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Section 1 (Line 3):
  Context: "...how has the Giver feels..."
  Alternatives: how the Giver feels, how the Giver felt
  
  Correction: how the Giver feels_____
```

**Skip review mode:**
```bash
--skip-review  # Auto-accepts all transcriptions
```

---

### Stage 3: Evaluation

**Programmatic rubric implementation:**

1. Extract TVODE components from text
2. Score SM1 (Component Presence) → determines ceiling
3. Score SM2 (Density Performance) within ceiling
4. Score SM3 (Cohesion Performance) within ceiling
5. Calculate overall score

**Output:**
```
outputs/evaluations/Coden_Week_4_tvode_evaluation.json
outputs/reports/Coden_Week_4_tvode_report.md
```

---

### Stage 4: Report Card

**Clean, one-line per SM format:**

```
SM1 (Component Presence): 4.0/5
Has all TVODE components with textual quotes - details are specific.

SM2 (Density Performance): 3.5/5
Makes 2 distinct analytical claims about POV and narrator reliability.

SM3 (Cohesion Performance): 3.0/5
Uses connectors but has 4 grammar errors (subject-verb agreement).

ONE-LINE FIX:
"description are limited" → "narrator describes only Jonas's sensations"
```

**Output:**
```
outputs/reports/Coden_Week_4_tvode_report.md
```

---

## Requirements

```bash
pip install anthropic --break-system-packages
export ANTHROPIC_API_KEY="your-key-here"
```

---

## Testing

### Test Transcription Only

```bash
python transcribe.py \
  --image student_work.jpg \
  --student "Test" \
  --assignment "Test"
```

### Test Evaluation Only

```bash
python evaluate.py \
  --transcript outputs/transcripts/Coden_Week_4_transcript.json \
  --evaluator tvode
```

### Test Full Pipeline

```bash
python automate.py \
  --image student_work.jpg \
  --student "Coden" \
  --assignment "Week 4" \
  --evaluator tvode
```

---

## Accuracy Validation

**Coden Week 4 Results:**

| Component | Manual | Programmatic | Match? |
|-----------|--------|--------------|--------|
| SM1 | 4.0 | 4.0 | ✅ |
| SM2 | 3.5 | 3.5 | ✅ |
| SM3 | 3.0 | 3.0 | ✅ |
| **Overall** | **3.6/5** | **3.6/5** | ✅ |

**Transcription accuracy:** 95%+ on clear handwriting

---

## Cost Estimates

**Per student (single image):**
- Transcription: ~$0.05-0.15 (depending on image size)
- Evaluation: ~$0.10-0.30 (includes full rubric context)
- **Total: ~$0.15-0.45 per student**

**Batch (20 students):**
- Total: ~$3-9 for complete diagnostics

---

## Customization

### Adjust Confidence Threshold

Edit `src/transcriber/core.py`:

```python
def _needs_review(self, uncertainties, handwriting_quality, accuracy_score):
    # Current: 90% auto-accept threshold
    if accuracy_score >= 0.90:  # Change to 0.95 for stricter
        return False
```

### Modify Scoring Logic

Edit `src/evaluators/tvode/scoring.py`:

```python
def score_sm2(self, text, components, ceiling):
    # Adjust distinct insight counting
    if distinct_insights >= 3:  # Make stricter/looser
        return 3.0
```

### Change Report Format

Edit `evaluate.py` or `automate.py`:

```python
# In the report generation section
report = f"""# Custom Report Format
...
"""
```

### Add New Evaluator

See main `README.md` for instructions on adding evaluators to the registry.

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### JSON parsing errors in transcription

Claude sometimes wraps JSON in markdown. The transcriber strips this automatically, but if it fails:

1. Check `transcripts/*.json` manually
2. Look for ```json wrappers
3. Report the issue for prompt improvement

### Scores seem too high/low

1. Compare with manual evaluations on 5-10 samples
2. Adjust thresholds in `src/evaluators/tvode/scoring.py`
3. Check if detail quality assessment matches your judgment

---

## Next Steps

**Immediate:**
1. Test on 5 more students to validate accuracy
2. Adjust scoring thresholds based on results
3. Build batch processing workflow

**Future enhancements:**
- Web interface for review stage
- Progress tracking across assignments
- Comparative analytics (Week 2 → Week 3 → Week 4)
- Export to CSV for spreadsheet analysis

---

## Support

Issues or questions? Check:
1. Project files: `v3_3_TVODE_Rubric.md`
2. Existing evaluations for comparison
3. Developer guide (if available)

---

**END OF README**
