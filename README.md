# Diagnostic Automated Workflow

Automated pipeline for transcribing handwritten student work and evaluating it against rubrics.

## Overview

This system provides a modular, extensible pipeline for:
1. **Transcription**: Converting handwritten images to structured JSON transcripts
2. **Evaluation**: Scoring transcripts against rubrics using pluggable evaluators
3. **Reporting**: Generating detailed report cards and evaluation summaries

## Quick Start

### Installation

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

### Basic Usage

**Option 1: Full pipeline (transcribe + evaluate)**
```bash
python automate.py \
  --image student_work.jpg \
  --student "Coden" \
  --assignment "Week 4" \
  --evaluator tvode
```

**Option 2: Step-by-step (recommended for review)**
```bash
# Step 1: Transcribe
python transcribe.py \
  --image student_work.jpg \
  --student "Coden" \
  --assignment "Week 4"

# Step 2: Review transcript (if needed)
# Edit outputs/transcripts/Coden_Week_4_transcript.json

# Step 3: Evaluate
python evaluate.py \
  --transcript outputs/transcripts/Coden_Week_4_transcript.json \
  --evaluator tvode
```

## Project Structure

```
diagnostic-automated-workflow/
├── transcribe.py          # Stage 1: Image → JSON transcript
├── evaluate.py            # Stage 2: Transcript → Evaluation
├── automate.py            # Full pipeline wrapper
│
├── src/
│   ├── transcriber/       # Transcription engine
│   │   ├── __init__.py
│   │   └── core.py        # TVODETranscriber implementation
│   │
│   └── evaluators/        # Evaluator registry
│       ├── __init__.py    # Registry: get_evaluator(), list_evaluators()
│       ├── tvode/         # TVODE rubric evaluator
│       │   ├── evaluator.py      # Main evaluator class
│       │   ├── api_evaluator.py  # API-based evaluation (default)
│       │   ├── components.py     # Component extraction
│       │   ├── scoring.py        # Rule-based scoring logic
│       │   ├── feedback.py      # Feedback generation
│       │   ├── taxonomies.py    # Rubric taxonomies
│       │   └── device_context.py # Device context handling
│       │
│       └── thesis/        # DCCEPS-based thesis evaluator
│           ├── __init__.py
│           ├── evaluator.py           # Main evaluator class
│           ├── thesis_components.py   # Component extraction
│           ├── thesis_scoring.py      # Scoring logic
│           ├── thesis_feedback.py     # Feedback generation
│           └── thesis_taxonomies.py   # DCCEPS patterns and taxonomies
│
├── tests/
│   └── test_thesis_evaluator.py  # Comprehensive tests for thesis evaluator
│
├── outputs/
│   ├── transcripts/       # JSON transcripts from Stage 1
│   ├── evaluations/       # JSON evaluations from Stage 2
│   ├── reports/           # Markdown report cards
│   └── report_cards/     # Text report cards
│
├── kernels/               # Device context files (optional)
├── reasoning/            # Reasoning documents (optional)
└── student_work/         # Student work images (by week)
```

## CLI Commands

### `transcribe.py`

Transcribes handwritten images to structured JSON.

```bash
python transcribe.py \
  --image page1.jpg [page2.jpg ...] \
  --student "Student Name" \
  --assignment "Week 4" \
  [--output ./outputs/transcripts]
```

**Output:** `outputs/transcripts/{student}_{assignment}_transcript.json`

**Features:**
- Multi-page support
- Confidence scoring
- Uncertainty flagging for review

### `evaluate.py`

Evaluates a transcript against a rubric. Uses API-based evaluation by default for higher accuracy.

```bash
python evaluate.py \
  --transcript transcript.json \
  --evaluator tvode \
  [--kernel kernels/The_Giver.json] \
  [--reasoning reasoning/The_Giver_ReasoningDoc.md] \
  [--output ./outputs] \
  [--rule-based]  # Use rule-based instead of API-based
  [--api-key sk-ant-...]  # Custom API key
```

**Output:**
- `outputs/evaluations/{student}_{assignment}_{evaluator}_evaluation.json`
- `outputs/reports/{student}_{assignment}_{evaluator}_report.md`

**Available evaluators:**
- `tvode` - TVODE rubric v3.3 implementation (API-based by default, rule-based fallback available)
- `thesis` - DCCEPS-based thesis evaluator for argumentative writing assessment

**Evaluation modes:**
- **API-based (default)**: Uses Claude API for more accurate, nuanced scoring
- **Rule-based**: Uses programmatic rules (faster, lower cost, less accurate)

### `automate.py`

Runs the full pipeline (transcribe → evaluate) in one command.

```bash
python automate.py \
  --image student_work.jpg \
  --student "Coden" \
  --assignment "Week 4" \
  --evaluator tvode \
  [--kernel kernels/The_Giver.json] \
  [--skip-review]  # Auto-accept transcription
```

## Evaluator System

The system uses a registry pattern for evaluators, making it easy to add new rubrics.

### Available Evaluators

- **tvode**: TVODE rubric v3.3 (Component Presence, Density, Cohesion)
  - Supports both API-based and rule-based evaluation
  - Includes device context detection and fuzzy matching
  - Generates detailed feedback and report cards

- **thesis**: DCCEPS-based thesis evaluator
  - Evaluates argumentative/thesis writing (e.g., "Is Jonas more hero or victim?")
  - Assesses position clarity, evidence quality, and reasoning depth
  - Detects DCCEPS layers (1-4): Definition → Comparison → Cause-Effect → Problem-Solution
  - Generates layer-specific feedback for progression
  - Available via CLI: `--evaluator thesis`

### Adding a New Evaluator

1. Create a new directory under `src/evaluators/`:
   ```bash
   mkdir -p src/evaluators/my_evaluator
   ```

2. Implement the evaluator class:
   ```python
   # src/evaluators/my_evaluator/evaluator.py
   class MyEvaluator:
       def evaluate(self, data, **kwargs):
           # Your evaluation logic
           return EvaluationResult(...)
   ```

3. Register in `src/evaluators/__init__.py`:
   ```python
   from .my_evaluator import MyEvaluator
   
   EVALUATORS = {
       'tvode': TVODEEvaluator,
       'my_evaluator': MyEvaluator,  # Add here
   }
   ```

4. Use it:
   ```bash
   python evaluate.py --transcript transcript.json --evaluator my_evaluator
   ```

## Output Formats

### Transcript JSON

```json
{
  "student_name": "Coden",
  "assignment": "Week 4",
  "transcription": "Full text...",
  "word_count": 250,
  "accuracy_score": 0.95,
  "requires_review": false,
  "uncertainties": []
}
```

### Evaluation JSON

```json
{
  "student": "Coden",
  "assignment": "Week 4",
  "evaluator": "tvode",
  "scores": {
    "sm1": 4.0,
    "sm2": 3.5,
    "sm3": 3.0,
    "overall": 3.6,
    "total_points": 18.0,
    "ceiling": 5
  },
  "components": {...},
  "feedback": {...}
}
```

## Requirements

- Python 3.8+
- `anthropic` package
- `ANTHROPIC_API_KEY` environment variable

## Cost Estimates

**Per student (single image):**
- Transcription: ~$0.05-0.15 (depending on image size)
- Evaluation (API-based): ~$0.10-0.30 (includes full rubric context)
- Evaluation (rule-based): ~$0.00 (no API calls)
- **Total (API-based): ~$0.15-0.45 per student**
- **Total (rule-based): ~$0.05-0.15 per student**

**Multi-page documents:**
- Add ~$0.05-0.15 per additional page for transcription
- Evaluation cost remains the same (single combined evaluation)

## Troubleshooting

### API Key Issues
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Import Errors
```bash
# Verify structure
python3 -c "from src.evaluators import list_evaluators; print(list_evaluators())"
# Should print: ['tvode', 'thesis']
```

### Evaluation Mode Selection
- By default, `evaluate.py` uses API-based evaluation for better accuracy
- Use `--rule-based` flag for faster, lower-cost rule-based evaluation
- API-based evaluation provides more nuanced scoring and better feedback

### Review Needed
If transcription requires review, edit the JSON file manually, then run `evaluate.py` separately.

## Development

See `README_AUTOMATION.md` for detailed pipeline documentation and customization options.

### Testing

Test individual components:
```bash
# Test transcription
python transcribe.py --image student_work.jpg --student "Test" --assignment "Test"

# Test evaluation
python evaluate.py --transcript outputs/transcripts/Coden_Week_4_transcript.json --evaluator tvode

# Test full pipeline
python automate.py --image student_work.jpg --student "Coden" --assignment "Week 4" --evaluator tvode
```

### Recent Updates

- **API-based evaluation**: TVODE evaluator now defaults to API-based evaluation for improved accuracy
- **Multi-page support**: Transcribe multiple pages in a single command
- **Modular architecture**: Separated transcription and evaluation stages for better workflow control
- **Device context**: Automatic device detection and fuzzy matching for kernel context

## License

[Add your license here]

