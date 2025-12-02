"""
Thesis API Evaluator - Claude judges argument quality

Hybrid approach:
- Rule-based extraction (thesis_components.py) finds patterns
- API scoring (this file) judges meaning and quality

This solves the position detection problem where pattern-counting
fails to understand argument direction, counter-arguments, and
weighing language.
"""

import json
import os
import re
from typing import Dict, Optional

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


def get_dcceps_expectations(year_level: int) -> dict:
    """
    Return DCCEPS expectations for year level
    
    Returns:
        dict with min_layer, max_layer, and scoring thresholds
    """
    if year_level <= 8:
        return {
            'min_layer': 2,
            'max_layer': 3,
            'label': 'DC-DCCE',
            'below_score': (2.0, 2.5),    # L1
            'at_min_score': (3.0, 3.5),   # L2
            'at_max_score': (4.0, 4.5),   # L3
            'exceeds_score': (4.75, 5.0)  # L4
        }
    elif year_level <= 10:
        return {
            'min_layer': 3,
            'max_layer': 4,
            'label': 'DCCE-DCCEPS',
            'below_score': (2.0, 2.5),    # L1-2
            'at_min_score': (3.0, 3.5),   # L3
            'at_max_score': (4.0, 4.5),   # L4
            'exceeds_score': (4.75, 5.0)  # N/A (L4 is max)
        }
    else:  # Year 11+
        return {
            'min_layer': 4,
            'max_layer': 4,
            'label': 'Full DCCEPS',
            'below_score': (2.0, 3.0),    # L1-3
            'at_min_score': (4.0, 4.5),   # L4
            'at_max_score': (4.0, 4.5),   # L4
            'exceeds_score': (4.75, 5.0)  # N/A
        }


def score_dcceps_relative(layer: int, year_level: int) -> float:
    """Score DCCEPS layer relative to year level expectations"""
    
    exp = get_dcceps_expectations(year_level)
    
    if layer < exp['min_layer']:
        # Below expected range
        return exp['below_score'][1]  # 2.5
    elif layer == exp['min_layer']:
        # At lower bound
        return exp['at_min_score'][1]  # 3.5
    elif layer == exp['max_layer']:
        # At upper bound
        return exp['at_max_score'][1]  # 4.5
    elif layer > exp['max_layer']:
        # Exceeds expectations
        return exp['exceeds_score'][1]  # 5.0
    else:
        # Between min and max (e.g., L3 when range is L2-4)
        return 4.0


THESIS_RUBRIC_PROMPT = """
## DCCEPS Thesis Rubric

### Position Assessment
Determine what position the student CONCLUDES with (not just mentions):

- **Strong:** "I believe...", "It is clear that...", "Jonas is definitely...", explicit stance
- **Moderate:** "I think...", "In my opinion...", "It seems that..."
- **Hedged:** "Maybe...", "Perhaps...", "Could be...", "might be considered..."
- **Implicit:** Position inferrable but not directly stated

**CRITICAL:** Counter-argument sections acknowledge the OTHER side but don't represent the student's position.
- "Although Jonas shows heroism..." followed by "his suffering outweighs..." → Position is VICTIM
- "While he is a victim..." followed by "his actions prove heroism" → Position is HERO
- Look at FINAL conclusion and weighing language ("outweighs", "more than", "ultimately")

### DCCEPS Layers (Critical - read carefully)

| Layer | Name | Description | Example |
|-------|------|-------------|---------|
| 1 | Definition | Just states position | "Jonas is a victim" |
| 2 | Comparison | Distinguishes alternatives | "MORE victim THAN hero because..." |
| 3 | Cause-Effect | Shows HOW evidence supports | "BECAUSE X, he experienced Y, WHICH CAUSED Z" |
| 4 | Problem-Solution | Frames authorial PURPOSE | "The text positions Jonas as victim IN ORDER TO critique..." |

**Layer Detection Rules:**
- Layer 1: Position stated, no reasoning
- Layer 2: Uses comparison language (more/less than, rather than, instead of)
- Layer 3: Uses causal language (because, therefore, which caused, as a result, this led to)
- Layer 4: Uses purpose language (in order to, so that, to show, the author uses X to)

### Evidence Quality

- **Specific:** Direct quotes with attribution - "Jonas says 'why don't we have snow?'"
- **Paraphrased:** References specific scenes - "when Jonas asks about snow"
- **General:** Vague references - "in the book...", "Jonas shows..."
- **Missing:** No textual support, pure assertion

**IMPORTANT:** Presence of quotation marks with text content = AT LEAST paraphrased, likely specific.

### Counter-Argument Assessment

Does the student acknowledge the OTHER side before dismissing it?
- Full: "Although Jonas shows heroism in escaping, his suffering throughout outweighs this"
- Partial: Brief mention of alternative without engagement
- None: Only argues one side

### Synthesis Assessment

Does conclusion WEIGH evidence rather than just restate position?
- Strong: "Therefore, when we consider X, Y, and Z together, it's clear that..."
- Moderate: Returns to position with some new insight
- Weak: Just restates opening position
- None: No conclusion or abrupt ending

### Scoring Ceilings (SM1 determines ceiling for SM2/SM3)

| Evidence Quality | SM1 Score | Ceiling |
|-----------------|-----------|---------|
| Missing | 1.0-1.5 | 2.0 |
| General | 2.0-2.5 | 3.0 |
| Paraphrased | 3.0-3.5 | 4.0 |
| Specific (quotes) | 4.0-5.0 | 5.0 |

**SM2 (DCCEPS Layer):**
- Layer 4 + specific evidence: 4.5-5.0
- Layer 3 + specific evidence: 3.5-4.0
- Layer 2 + paraphrased: 2.5-3.0
- Layer 1 only: 1.5-2.0

**SM3 (Coherence):**
- Counter-arg + synthesis + flow: 4.5-5.0
- Synthesis OR counter-arg: 3.0-4.0
- Basic flow only: 2.0-3.0
- Contradictions or no structure: 1.0-2.0
"""


YEAR_LEVEL_SECTION = """
---

## YEAR LEVEL EXPECTATIONS (Critical for Scoring)

Student year level: {year_level}
Expected DCCEPS range: Layer {min_layer}-{max_layer} ({expectation_label})

**Scoring SM2 (Reasoning Depth) relative to expectations:**

| Performance | Score |
|-------------|-------|
| Below Layer {min_layer} | 2.0-2.5 |
| At Layer {min_layer} | 3.0-3.5 |
| At Layer {max_layer} | 4.0-4.5 |
| Above Layer {max_layer} | 5.0 |

**Do NOT penalize for not reaching Layer 4 if student is Year 7-8.**
**DO acknowledge when student exceeds their year level expectations.**
"""


STAGE1_CHECK = """
---

## Stage 1 Integration (Soft Check)

Check if thesis references elements from Weeks 1-4:
- Literary devices (foreshadowing, imagery, symbolism)
- Narrative voice (POV, focalization)
- Structure (exposition, climax, resolution)

This is a **soft requirement**:
- Mentioning these strengthens the thesis
- NOT mentioning them doesn't hard-cap the score
- Student can still score 4.5 without detailed quotes
- Note in feedback if integration is strong/weak
"""


ALIGNMENT_MODE_CHECK = """
---

## Alignment Mode Detection (Feedback Only - Not Scored)

Identify which organizing principle the student's thesis follows:

1. **Narrative-Driven:** Follows story chronology (Ch1 → Ch3 → Ch11)
2. **Structure-Driven:** Follows Freytag phases (exposition → climax)
3. **Voice-First:** Foregrounds narration as controlling element

Note the detected mode in feedback. Students are developing this skill.
"""


THESIS_EVALUATION_PROMPT = """
You are evaluating a student's argumentative writing about whether Jonas (from The Giver) is more hero or victim.

{rubric}

---

## Student Text

{text}

---

## Pre-Extracted Signals (for reference only - use your judgment)

Evidence items found: {evidence_count}
Reasoning patterns detected: {reasoning_types}
Counter-argument signals: {counter_signals}
Synthesis markers present: {has_synthesis}

---

## Your Task

1. **Determine Position** - What position does the student CONCLUDE with?
   - Look at their FINAL argument, not just word counts
   - Counter-argument sections acknowledge the other side but don't represent the student's position
   - "Although X... but Y" means Y is their position
   - Weighing language ("outweighs", "more than") indicates final position

2. **Assess DCCEPS Layer** - How sophisticated is the reasoning?
   - Layer 1: Just labels (Definition) - "Jonas is a victim"
   - Layer 2: Compares alternatives (Comparison) - "more victim than hero"
   - Layer 3: Shows cause-effect chains (Cause-Effect) - "because X, which caused Y"
   - Layer 4: Frames authorial purpose (Problem-Solution) - "to show that..."

3. **Score SM1** (Position + Evidence) → This sets the ceiling
   - Check: Does student include EXACT QUOTES from the text?
   - If YES (quotes in quotation marks): Evidence is specific (ceiling 4.5-5.0)
   - If paraphrased (references scenes without quotes): ceiling 4.0
   - If general descriptions only: ceiling 3.0
   - If no evidence: ceiling 2.0

4. **Score SM2** (Reasoning Depth) WITHIN the ceiling
   - Based on DCCEPS layer reached
   - Cannot exceed SM1 ceiling

5. **Score SM3** (Argument Coherence) WITHIN the ceiling
   - Counter-argument acknowledgment
   - Synthesis quality
   - Cannot exceed SM1 ceiling

6. **Generate feedback** - Specific to their writing, positive framing

---

## Output Format (JSON only, no markdown code blocks)

{{
  "position": "hero|victim|both_acknowledged|unclear",
  "position_strength": "strong|moderate|hedged|implicit",
  "position_reasoning": "<one sentence explaining how you determined position>",
  
  "dcceps_layer": <1-4>,
  "dcceps_label": "Definition|Comparison|Cause-Effect|Problem-Solution",
  "dcceps_reasoning": "<one sentence explaining layer assessment>",
  
  "evidence_quality": "specific|paraphrased|general|missing",
  "has_counter_argument": <true|false>,
  "has_synthesis": <true|false>,
  
  "sm1_score": <float 1.0-5.0>,
  "sm2_score": <float, must be <= ceiling from SM1>,
  "sm3_score": <float, must be <= ceiling from SM1>,
  "ceiling": <float based on evidence quality>,
  
  "feedback": {{
    "sm1": "<what's working with position/evidence>",
    "sm1_next": "<one concrete improvement for evidence>",
    "sm2": "<what's working with reasoning>",
    "sm2_next": "<one concrete improvement - how to reach next DCCEPS layer>",
    "sm3": "<what's working with structure>",
    "sm3_next": "<one concrete improvement for coherence>",
    "dcceps_guidance": "<specific advice on reaching next layer>",
    "stage1_integration": "<weak|moderate|strong> - <brief note on device/voice/structure mentions>",
    "alignment_mode": "narrative|structure|voice|unclear",
    "alignment_mode_note": "<guidance on developing this further>"
  }}
}}
"""


def evaluate_thesis_with_api(
    text: str,
    components=None,
    api_key: Optional[str] = None,
    year_level: int = 8
) -> Dict:
    """
    Evaluate thesis using Claude API
    
    Args:
        text: Student's argumentative writing
        components: Pre-extracted ThesisComponents (optional, for context)
        api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
        year_level: Student year level (7-12, default: 8)
    
    Returns:
        Dict with position, dcceps_layer, scores, feedback
    """
    
    if Anthropic is None:
        raise ImportError("anthropic package required: pip install anthropic --break-system-packages")
    
    key = api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set. Set environment variable or pass api_key parameter.")
    
    # Extract component info for context (if provided)
    if components is not None:
        evidence_count = len(getattr(components, 'evidence_items', []))
        reasoning_types = list(getattr(components, 'reasoning_types', {}).keys())
        counter_signals = len(getattr(components, 'counter_arguments', []))
        has_synthesis = bool(getattr(components, 'synthesis', None))
    else:
        # Fallback: basic detection for context
        evidence_count = len(re.findall(r'"[^"]{5,}"', text))
        reasoning_types = []
        if re.search(r'\bbecause\b', text, re.I):
            reasoning_types.append('cause_effect')
        if re.search(r'\bmore\s+\w+\s+than\b', text, re.I):
            reasoning_types.append('comparison')
        counter_signals = len(re.findall(r'\b(although|however|while|despite)\b', text, re.I))
        has_synthesis = bool(re.search(r'\b(therefore|thus|in conclusion|overall)\b', text, re.I))
    
    # Get expectations for year level
    exp = get_dcceps_expectations(year_level)
    
    # Build year level section
    year_section = YEAR_LEVEL_SECTION.format(
        year_level=year_level,
        min_layer=exp['min_layer'],
        max_layer=exp['max_layer'],
        expectation_label=exp['label']
    )
    
    # Build full rubric with year level expectations
    full_rubric = THESIS_RUBRIC_PROMPT + year_section + STAGE1_CHECK + ALIGNMENT_MODE_CHECK
    
    # Build prompt
    prompt = THESIS_EVALUATION_PROMPT.format(
        rubric=full_rubric,
        text=text,
        evidence_count=evidence_count,
        reasoning_types=reasoning_types,
        counter_signals=counter_signals,
        has_synthesis=has_synthesis
    )
    
    # Call API
    client = Anthropic(api_key=key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = response.content[0].text.strip()
    
    # Handle markdown wrapping (sometimes API wraps in ```json)
    if response_text.startswith('```'):
        lines = response_text.split('\n')
        json_lines = []
        in_json = False
        for line in lines:
            if line.startswith('```') and not in_json:
                in_json = True
                continue
            elif line.startswith('```') and in_json:
                break
            elif in_json:
                json_lines.append(line)
        response_text = '\n'.join(json_lines)
    
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse API response as JSON: {e}\nResponse: {response_text[:500]}")
    
    # Validation: Check for quotes in text vs evidence quality
    has_quotes = bool(re.search(r'"[^"]{10,}"', text))  # Quote with 10+ chars
    if has_quotes and result.get('evidence_quality') in ('general', 'missing'):
        print("  ⚠ API marked evidence as general/missing but quotes detected - adjusting")
        result['evidence_quality'] = 'paraphrased'
        result['ceiling'] = max(result.get('ceiling', 3.0), 4.0)
        result['sm1_score'] = max(result.get('sm1_score', 2.5), 3.5)
    
    # Enforce ceiling logic
    ceiling = result.get('ceiling', 5.0)
    if result.get('sm2_score', 0) > ceiling:
        result['sm2_score'] = ceiling
    if result.get('sm3_score', 0) > ceiling:
        result['sm3_score'] = ceiling
    
    # Post-API validation: Override SM2 with year-relative scoring
    detected_layer = result.get('dcceps_layer', 2)
    expected_sm2 = score_dcceps_relative(detected_layer, year_level)
    if abs(result.get('sm2_score', 0) - expected_sm2) > 0.5:
        print(f"  ⚠ Adjusting SM2: {result['sm2_score']} → {expected_sm2} (year-relative)")
        result['sm2_score'] = min(expected_sm2, ceiling)  # Still respect ceiling
    
    # Store year level info
    result['year_level'] = year_level
    result['expected_dcceps_range'] = f"L{exp['min_layer']}-L{exp['max_layer']}"
    
    # Add year-level acknowledgment to feedback
    layer = result.get('dcceps_layer', 2)
    if 'feedback' not in result:
        result['feedback'] = {}
    
    if layer > exp['max_layer']:
        result['feedback']['year_level_note'] = (
            f"Exceptional! You've reached Layer {layer} ({result.get('dcceps_label', '')}), "
            f"which exceeds Year {year_level} expectations (Layer {exp['max_layer']})."
        )
    elif layer >= exp['min_layer']:
        result['feedback']['year_level_note'] = (
            f"You're meeting Year {year_level} expectations with Layer {layer} reasoning."
        )
    else:
        layer_names = ['', 'Definition', 'Comparison', 'Cause-Effect', 'Problem-Solution']
        result['feedback']['year_level_note'] = (
            f"Work toward Layer {exp['min_layer']} ({layer_names[exp['min_layer']]}) "
            f"reasoning for Year {year_level} level."
        )
    
    # Ensure feedback has default values for new fields if missing
    if 'stage1_integration' not in result.get('feedback', {}):
        result['feedback']['stage1_integration'] = 'moderate - Some integration of literary elements'
    if 'alignment_mode' not in result.get('feedback', {}):
        result['feedback']['alignment_mode'] = 'unclear'
    if 'alignment_mode_note' not in result.get('feedback', {}):
        result['feedback']['alignment_mode_note'] = 'Consider organizing by narrative, structure, or voice'
    
    # Recalculate overall score with adjusted SM2
    sm1 = result.get('sm1_score', 3.0)
    sm2 = result.get('sm2_score', 2.5)
    sm3 = result.get('sm3_score', 2.5)
    result['overall_score'] = round((sm1 * 0.4) + (sm2 * 0.3) + (sm3 * 0.3), 2)
    result['total_points'] = round(result['overall_score'] * 5, 1)
    
    return result


def evaluate_thesis_batch(
    texts: Dict[str, str],
    api_key: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Dict]:
    """
    Evaluate multiple student texts
    
    Args:
        texts: Dict mapping student_name -> text
        api_key: Anthropic API key
        verbose: Print progress
    
    Returns:
        Dict mapping student_name -> evaluation result
    """
    results = {}
    total = len(texts)
    
    for i, (name, text) in enumerate(texts.items(), 1):
        if verbose:
            print(f"[{i}/{total}] Evaluating {name}...")
        try:
            results[name] = evaluate_thesis_with_api(text, api_key=api_key)
            if verbose:
                pos = results[name].get('position', 'unknown')
                layer = results[name].get('dcceps_layer', 0)
                overall = results[name].get('overall_score', 0)
                print(f"  ✓ Position: {pos}, Layer: {layer}, Overall: {overall}/5")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[name] = {'error': str(e)}
    
    return results


def generate_thesis_report(result: Dict, student_name: str = "Student") -> str:
    """
    Generate a formatted report from API evaluation result
    
    Args:
        result: Dict from evaluate_thesis_with_api
        student_name: Name for report header
    
    Returns:
        Formatted string report
    """
    if 'error' in result:
        return f"# {student_name} - Thesis Evaluation\n\n**Error:** {result['error']}"
    
    feedback = result.get('feedback', {})
    
    report = f"""# {student_name} - Thesis Evaluation

## Position Analysis
- **Position:** {result.get('position', 'unknown').title()}
- **Strength:** {result.get('position_strength', 'unknown').title()}
- **Reasoning:** {result.get('position_reasoning', 'N/A')}

## DCCEPS Layer
- **Layer:** {result.get('dcceps_layer', 0)} ({result.get('dcceps_label', 'Unknown')})
- **Assessment:** {result.get('dcceps_reasoning', 'N/A')}

## Scores
| Sub-Metric | Score | Ceiling |
|------------|-------|---------|
| SM1 (Position + Evidence) | {result.get('sm1_score', 0):.1f}/5 | {result.get('ceiling', 5):.1f} |
| SM2 (Reasoning Depth) | {result.get('sm2_score', 0):.1f}/5 | {result.get('ceiling', 5):.1f} |
| SM3 (Coherence) | {result.get('sm3_score', 0):.1f}/5 | {result.get('ceiling', 5):.1f} |
| **Overall** | **{result.get('overall_score', 0):.1f}/5** | |
| **Total Points** | **{result.get('total_points', 0):.1f}/25** | |

## Evidence Quality
- **Quality:** {result.get('evidence_quality', 'unknown').title()}
- **Counter-Argument:** {'Yes' if result.get('has_counter_argument') else 'No'}
- **Synthesis:** {'Yes' if result.get('has_synthesis') else 'No'}

## Feedback

### SM1: Position & Evidence
**What's working:** {feedback.get('sm1', 'N/A')}
**Next step:** {feedback.get('sm1_next', 'N/A')}

### SM2: Reasoning Depth
**What's working:** {feedback.get('sm2', 'N/A')}
**Next step:** {feedback.get('sm2_next', 'N/A')}

### SM3: Coherence
**What's working:** {feedback.get('sm3', 'N/A')}
**Next step:** {feedback.get('sm3_next', 'N/A')}

### DCCEPS Guidance
{feedback.get('dcceps_guidance', 'N/A')}
"""
    return report


# CLI support
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate thesis with API")
    parser.add_argument('--text', type=str, help='Text to evaluate')
    parser.add_argument('--file', type=str, help='File containing text to evaluate')
    parser.add_argument('--api-key', type=str, help='Anthropic API key')
    parser.add_argument('--output', type=str, help='Output file for report')
    
    args = parser.parse_args()
    
    # Get text
    if args.file:
        with open(args.file, 'r') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        print("Error: Provide --text or --file")
        exit(1)
    
    # Evaluate
    print("Evaluating thesis...")
    result = evaluate_thesis_with_api(text, api_key=args.api_key)
    
    # Generate report
    report = generate_thesis_report(result)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)
