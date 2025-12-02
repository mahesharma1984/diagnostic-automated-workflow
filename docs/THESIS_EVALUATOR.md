# Thesis Evaluator Documentation

## Overview

The Thesis Evaluator is a DCCEPS-based evaluation system for assessing argumentative/thesis writing. It parallels the TVODE evaluator architecture but focuses on argumentative structure rather than analytical sentence structure.

**DCCEPS Framework:**
- **D**efinition → **C**omparison → **C**ause-**E**ffect → **P**roblem-**S**olution
- These represent 4 layers of argumentative sophistication (Layer 1-4)
- Students progress from simply stating a position (L1) to framing the purpose of their argument (L4)

## When to Use

Use the thesis evaluator when students are writing argumentative pieces, such as:
- "Is Jonas more hero or victim?"
- "Should the community have continued as it was?"
- Any prompt requiring students to take a position and support it with evidence

The TVODE evaluator assesses analytical sentence structure (Topic-Verb-Object-Detail-Effect), while the thesis evaluator assesses reasoning structure.

## Quick Start

### CLI Usage

```bash
python evaluate.py \
  --transcript outputs/transcripts/Student_Week_5_transcript.json \
  --evaluator thesis
```

### Python API

```python
from src.evaluators.thesis import ThesisEvaluator

evaluator = ThesisEvaluator()
result = evaluator.evaluate("I believe Jonas is more of a victim because he suffered alone.")

print(f"DCCEPS Layer: {result.dcceps_layer} ({result.dcceps_label})")
print(f"Overall Score: {result.overall_score:.1f}/5")
print(result.feedback['dcceps_guidance'])
```

## DCCEPS Layers

### Layer 1: Definition
**What it is:** Just identifies/labels the position without explanation.

**Example:**
> "Jonas is a victim."

**Characteristics:**
- States position clearly
- May or may not include evidence
- No comparative reasoning
- No cause-effect logic

### Layer 2: Comparison
**What it is:** Distinguishes between alternatives (more X than Y).

**Example:**
> "Jonas is more of a victim than a hero because he suffered more than he helped."

**Characteristics:**
- Uses comparison language ("more than", "rather than", "unlike")
- Distinguishes between alternatives
- May include evidence but doesn't explain HOW it supports position

### Layer 3: Cause-Effect
**What it is:** Shows HOW evidence supports position through cause-effect reasoning.

**Example:**
> "Jonas is more of a victim because he was forced to receive memories. This caused him to experience isolation. Therefore, his suffering outweighs his heroism."

**Characteristics:**
- Uses cause-effect connectors ("because", "therefore", "which causes")
- Explains HOW evidence creates meaning
- Shows logical connections between evidence and position
- Requires at least 2 cause-effect reasoning chains

### Layer 4: Problem-Solution
**What it is:** Frames the purpose/function of the argument configuration.

**Example:**
> "I believe Jonas is more of a victim than a hero. Although he saved Gabriel, his suffering from receiving painful memories alone caused profound isolation. However, some might argue he was heroic for escaping. Nevertheless, the evidence shows he suffered more than he saved. Therefore, Jonas is ultimately more victim than hero."

**Characteristics:**
- All Layer 3 requirements (cause-effect reasoning)
- Acknowledges counter-arguments ("although", "however", "on the other hand")
- Includes synthesis/conclusion ("therefore", "ultimately", "the evidence shows")
- Frames the purpose of the argument

## Scoring System

The thesis evaluator uses three scoring metrics (SM1, SM2, SM3) parallel to TVODE:

### SM1: Position + Evidence (0-5 points)
- **Position Clarity (0-2 points):**
  - Clear position: +1.0
  - Strong/moderate stance: +1.0
  - Implicit stance: +0.5
- **Evidence Quality (0-3 points):**
  - Specific textual evidence (quotes, specific scenes): 3.0
  - Paraphrased evidence: 2.0
  - General reference: 1.0
  - Assertion only: 0.5
- **Quantity Penalty/Bonus:**
  - Single evidence item: -30% penalty
  - 4+ evidence items: +10% bonus (capped)

### SM2: Reasoning Depth (0-5 points)
- **Base Score from DCCEPS Layer:**
  - Layer 0 (no position): 1.5
  - Layer 1 (Definition): 2.5
  - Layer 2 (Comparison): 3.5
  - Layer 3 (Cause-Effect): 4.0
  - Layer 4 (Problem-Solution): 5.0
- **Quality Adjustments:**
  - Multiple distinct reasoning chains: +0.25 to +0.5 bonus
  - Short responses (<50 words): Cap at 3.0
  - Contradictions: -0.5 penalty

### SM3: Argument Coherence (0-5 points)
- **Base Score:** 2.0
- **Counter-argument acknowledgment:** +0.5 to +1.0
- **Synthesis quality:** +0.5 to +1.0
- **Flow markers:** +0.25 to +0.5
- **Grammar errors:** -0.5 to -1.0

### Overall Score
```
Overall = (SM1 × 0.40) + (SM2 × 0.30) + (SM3 × 0.30)
Total Points = Overall × 5
```

## Component Extraction

The evaluator extracts the following components:

### Position
- **Values:** `"hero"`, `"victim"`, `"both_acknowledged"`, `"unclear"`
- **Strength:** `"strong"`, `"moderate"`, `"hedged"`, `"implicit"`, `"missing"`

### Evidence
- **Quality:** `"specific"`, `"paraphrased"`, `"general"`, `"assertion"`, `"missing"`
- **Items:** List of evidence pieces found in text
- **Types:** Categorized by specificity (quotes, paraphrases, general references)

### Reasoning
- **Chains:** List of reasoning sentences
- **Types:** `cause_effect`, `comparison`, `elaboration`, `definition`

### Counter-arguments
- **List:** Sentences acknowledging the other side
- **Signals:** "however", "although", "on the other hand", etc.

### Synthesis
- **Statement:** Concluding/weighing statement
- **Markers:** "therefore", "ultimately", "the evidence shows", etc.

## Feedback Generation

The evaluator generates feedback in several categories:

### SM1 Feedback
- Current status of position clarity and evidence quality
- Next steps for improvement

### SM2 Feedback
- Current DCCEPS layer reached
- Count of reasoning types used
- Layer-specific progression guidance

### SM3 Feedback
- Counter-argument acknowledgment status
- Synthesis quality
- Suggestions for improvement

### DCCEPS Guidance
**Most important feedback** - tells students exactly how to reach the next layer:

- **Layer 0 → 1:** "Start with Layer 1 (Definition): State clearly whether Jonas is more hero or victim."
- **Layer 1 → 2:** "Move from Definition to Comparison. Show why he's MORE of one than the other."
- **Layer 2 → 3:** "Move from Comparison to Cause-Effect. Explain HOW the evidence creates meaning."
- **Layer 3 → 4:** "To reach Layer 4 (Problem-Solution), frame the PURPOSE of this configuration."

## Expected Results (Week 5 Samples)

| Student | Expected Score | Expected Layer | Key Features |
|---------|---------------|----------------|-------------|
| Desmond | 4.8-5.0/5 | Layer 4 | Counter-argument ("on the other hand"), synthesis ("therefore, it is evident"), strong position, specific quotes |
| Coden | 3.0-3.5/5 | Layer 3 | Clear position, cause-effect ("because", "therefore"), but no counter-argument |
| Davin | 2.5-3.5/5 | Layer 2-3 | Implicit position, very brief, contradictory logic ("is a victim" then "not really a victim") |

## Common Issues & Fixes

### Issue: All students scoring too high
**Fix:** Check `_extract_evidence()` - ensure it requires multiple specific items for "specific" quality rating.

### Issue: DCCEPS layer always 3
**Fix:** Check `_assess_dcceps_layer()` - Layer 4 requires counter-argument AND synthesis AND cause-effect.

### Issue: Contradictions not detected
**Fix:** Check `_has_contradictions()` - ensure patterns match "is a victim" + "not really a victim" without intervening "however/but".

### Issue: Feedback too generic
**Fix:** Check `_generate_dcceps_guidance()` - each layer should have distinct, actionable advice.

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_thesis_evaluator.py -v
```

Test categories:
- Component extraction (position, evidence, reasoning)
- DCCEPS layer detection (all 4 layers)
- Scoring accuracy (short responses, evidence quality, counter-arguments)
- Feedback generation (all feedback types)
- Edge cases (empty strings, contradictions)

## API Reference

### `ThesisEvaluator`

Main evaluator class.

**Methods:**
- `evaluate(text: str) -> ThesisEvaluationResult` - Evaluate a text string
- `evaluate_batch(texts: Dict[str, str]) -> Dict[str, ThesisEvaluationResult]` - Evaluate multiple texts
- `generate_report(result, student_name) -> str` - Generate markdown report

### `ThesisEvaluationResult`

Evaluation result dataclass.

**Attributes:**
- `sm1_score`, `sm2_score`, `sm3_score`: Individual scores
- `overall_score`: Weighted average (0-5)
- `total_points`: Total points (0-25)
- `dcceps_layer`: Layer number (1-4)
- `dcceps_label`: Layer name
- `components`: `ThesisComponents` object
- `feedback`: Dict of feedback strings

### `extract_thesis_components(text: str) -> ThesisComponents`

Extract all thesis components from text.

### `format_comparative_summary(results: Dict[str, ThesisEvaluationResult]) -> str`

Generate comparative summary table across multiple students.

## Examples

### Example 1: Layer 1 Response

```python
text = "Jonas is a victim."
result = evaluator.evaluate(text)

# Result:
# - dcceps_layer: 1
# - dcceps_label: "Definition"
# - sm1_score: ~2.0
# - sm2_score: ~2.5
```

### Example 2: Layer 4 Response

```python
text = """I believe Jonas is more of a victim than a hero. Although he saved Gabriel, 
his suffering from receiving painful memories alone caused profound isolation. 
However, some might argue he was heroic for escaping. Nevertheless, the evidence 
shows he suffered more than he saved. Therefore, Jonas is ultimately more victim than hero."""

result = evaluator.evaluate(text)

# Result:
# - dcceps_layer: 4
# - dcceps_label: "Problem-Solution"
# - sm1_score: ~4.5-5.0
# - sm2_score: ~5.0
# - sm3_score: ~4.5-5.0
```

## Integration with Pipeline

The thesis evaluator is fully integrated with the evaluation pipeline:

1. **Transcription:** Use `transcribe.py` to convert handwritten work to JSON
2. **Evaluation:** Use `evaluate.py --evaluator thesis` to evaluate
3. **Reports:** Automatically generates markdown reports with DCCEPS guidance

## References

- DCCEPS Framework: See `LEM__Stage_2__ARC_Framework_for_Logic_Articulation.pdf`
- Parallel Architecture: See TVODE evaluator in `src/evaluators/tvode/`
