"""
Thesis API Evaluator - Claude judges argument quality

Version: 2.1.1 (2025-12-04)
Component: Evaluator (Thesis) v2.1

Hybrid approach:
- Rule-based extraction (thesis_components.py) finds patterns
- API scoring (this file) judges meaning and quality

This solves the position detection problem where pattern-counting
fails to understand argument direction, counter-arguments, and
weighing language.

v2.1.1 Changes:
- Restore component signals to API prompt (evidence_count, cause_effect_count, counter_signals)
- Add hard validation that checks extracted counts, not API labels
- Cap SM1 at 2.5 when evidence_count=0 (regardless of API's evidence_quality claim)
- Cap DCCEPS layer at 2 when cause_effect_count=0

Results:
- Gabriel: 4.05 → 3.1 (correctly penalized for 0 evidence, 0 chains)
- Desmond: 3.75 → 3.55 (correctly scores higher than Gabriel)
- Coden: 4.05 → 4.05 (unchanged, has real substance)
- Order now reflects actual argument quality

Root Cause:
- Component extraction worked correctly
- API prompt was missing the extracted signals (implementation regression)
- API rewarded prose fluency over argument substance
- Validation checked API's label ("missing") not hard count (0)
"""

import json
import os
import re
from typing import Dict, Optional

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


# ============================================================
# CONTEXT EXTRACTION
# ============================================================

def extract_thesis_context(kernel_path: str) -> dict:
    """
    Extract book context from kernel for charitable interpretation.
    
    Args:
        kernel_path: Path to kernel JSON file
    
    Returns:
        dict with title, author, plot_arc, narrative_voice, 
        rhetorical_pattern, key_concepts, devices
    """
    
    with open(kernel_path, 'r') as f:
        kernel = json.load(f)
    
    context = {
        'title': kernel['metadata']['title'].strip(),
        'author': kernel['metadata']['author'].strip(),
    }
    
    # Plot arc summaries
    context['plot_arc'] = {
        section: kernel['extracts'][section]['rationale'][:250]
        for section in ['exposition', 'climax', 'resolution']
    }
    
    # Narrative voice
    voice = kernel['macro_variables']['narrative']['voice']
    context['narrative_voice'] = {
        'pov': voice['pov'],
        'pov_description': voice['pov_description'],
        'focalization': voice['focalization'],
    }
    
    # Rhetorical pattern
    rhetoric = kernel['macro_variables']['rhetoric']
    context['rhetorical_pattern'] = {
        'alignment_type': rhetoric['structure']['alignment_type'],
        'primary_mechanism': rhetoric['structure']['primary_mechanism'],
        'mediation_summary': kernel['macro_variables']['device_mediation']['summary'][:300],
    }
    
    # Devices (for recognition)
    context['devices'] = [d['name'] for d in kernel['micro_devices']]
    
    # Key concepts
    context['key_concepts'] = _extract_key_concepts(kernel)
    
    return context


def _extract_key_concepts(kernel: dict) -> list:
    """Extract key concepts from kernel for fuzzy matching."""
    
    concepts = set()
    
    # Extract capitalized words from extracts (likely proper nouns)
    for section, data in kernel['extracts'].items():
        caps = re.findall(r'\b[A-Z][a-z]+\b', data['rationale'])
        concepts.update(caps)
    
    # Add title and author
    concepts.add(kernel['metadata']['title'].strip())
    
    # Filter common words
    stopwords = {'The', 'This', 'These', 'Chapter', 'His', 'Her', 'And', 'With'}
    concepts = [c for c in concepts if c not in stopwords and len(c) > 2]
    
    return sorted(concepts)[:25]


# ============================================================
# CONTEXT TEMPLATE
# ============================================================

TEXT_CONTEXT_TEMPLATE = """
---

## Text Context: {title} by {author}

### Plot Arc
- **Exposition:** {exposition}
- **Climax:** {climax}  
- **Resolution:** {resolution}

### Narrative Voice
- **POV:** {pov} — {pov_description}
- **Focalization:** {focalization} (internal access to protagonist's thoughts)

### Rhetorical Pattern
- **Alignment:** {alignment_type} (transformative — personal journey = social critique)
- **Mechanism:** {primary_mechanism} (character development drives meaning)

### Key Concepts (recognize these even if misspelled)
{key_concepts}

### Devices Used
{devices}

---

**CRITICAL:** Use this context to CHARITABLY INTERPRET student work.
- If they reference these concepts (even imprecisely), they're engaging correctly
- Transcription may have errors — look for IDEAS, not exact phrases
- Score REASONING QUALITY, not surface accuracy
"""


def build_context_section(context: dict) -> str:
    """Build the TEXT_CONTEXT section from extracted context."""
    
    if not context:
        return ""
    
    return TEXT_CONTEXT_TEMPLATE.format(
        title=context['title'],
        author=context['author'],
        exposition=context['plot_arc'].get('exposition', 'N/A'),
        climax=context['plot_arc'].get('climax', 'N/A'),
        resolution=context['plot_arc'].get('resolution', 'N/A'),
        pov=context['narrative_voice']['pov'],
        pov_description=context['narrative_voice']['pov_description'],
        focalization=context['narrative_voice']['focalization'],
        alignment_type=context['rhetorical_pattern']['alignment_type'],
        primary_mechanism=context['rhetorical_pattern']['primary_mechanism'],
        key_concepts=', '.join(context.get('key_concepts', [])),
        devices=', '.join(context.get('devices', [])[:12]),
    )


# ============================================================
# YEAR LEVEL EXPECTATIONS
# ============================================================

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


def load_reasoning_context(reasoning_path: str) -> str:
    """Load reasoning doc and format as context for prompt injection."""
    
    with open(reasoning_path, 'r') as f:
        r = json.load(f)
    
    # Safely extract values with fallbacks
    voice = r.get('thesis_slots', {}).get('voice_label', 'N/A')
    theme = r.get('roadmap_slots', {}).get('theme_revealed', 'N/A')
    conflict = r.get('plot_slots', {}).get('conflict', 'N/A')
    outcome = r.get('plot_slots', {}).get('outcome', 'N/A')
    device_1 = r.get('thesis_slots', {}).get('device_1', 'N/A')
    device_2 = r.get('thesis_slots', {}).get('device_2', 'N/A')
    
    return f"""

## Book Context (use for charitable interpretation)

**Expected Voice:** {voice}
**Expected Theme:** {theme}
**Character Arc:** {conflict} → {outcome}
**Key Devices:** {device_1}, {device_2}

**Concepts to recognize (even if misspelled):**
- Jonas, Sameness, memories, Gabriel, Elsewhere, release
- transformation, awakening, conformity, individuality
- responsibility, emotions, family, identity

**INSTRUCTION:** If student text matches these concepts (even garbled), 
they are engaging correctly. Score REASONING, not transcription accuracy.
"""


THESIS_RUBRIC_PROMPT = """
## Thesis Evaluation Rubric (Interpretive)

### Position Assessment
Determine what position the student CONCLUDES with. Be charitable:

- **Clear:** Student explicitly states or strongly implies a position
- **Implicit:** Position inferrable from argument direction  
- **Unclear:** Cannot determine what student is arguing

**IMPORTANT:** 
- Counter-arguments acknowledge OTHER side but don't represent student's position
- Look at FINAL conclusion and overall argument direction
- Transcription errors may obscure phrasing — interpret the IDEAS

### DCCEPS Layers (Reasoning Depth)

| Layer | Name | What to Look For |
|-------|------|------------------|
| 1 | Definition | Just states what happens, labels character |
| 2 | Comparison | Distinguishes alternatives (more X than Y) |
| 3 | Cause-Effect | Shows HOW/WHY (because, therefore, which leads to) |
| 4 | Problem-Solution | Frames authorial purpose (in order to show) |

**Note:** Look for REASONING PATTERNS, not exact keywords. A student showing 
"memories → feelings → identity change" is doing L3 cause-effect reasoning.

### Themes and Concepts
Does the student identify relevant themes?
- Transformation/awakening
- Conformity vs individuality  
- Memory and emotion
- Responsibility and growth

### Device Awareness
Did they mention any literary devices? Imprecise mentions count:
- "third person" = Third Person Limited ✓
- "we see through Jonas" = focalization ✓

### Scoring (Year 7-8 Expectations: L2-L3)

**SM1: Position + Theme Identification (40%)**
- 4.5-5.0: Clear position + multiple themes + device awareness
- 3.5-4.0: Implicit position + identifies key themes
- 2.5-3.0: Unclear position + some relevant ideas
- 1.5-2.0: No position + mostly summary

**SM2: Reasoning Depth (30%)**
- 4.5-5.0: L3+ with multiple reasoning chains
- 3.5-4.0: L3 cause-effect OR strong L2
- 2.5-3.0: L2 comparison only
- 1.5-2.0: L1 definition only

**SM3: Argument Coherence (30%)**
Do ideas connect logically? (NOT grammar accuracy)
- 4.0-5.0: Clear arc, ideas build on each other
- 3.0-4.0: Ideas connect, structure visible
- 2.0-3.0: Loose connections
- 1.0-2.0: Incoherent

**CRITICAL:** 
- Transcription artifacts are NOT student errors
- Surface grammar errors don't reduce score if meaning is clear
- Evidence quality informs FEEDBACK, not score ceiling
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
You are evaluating a Year {year_level} student's thesis writing.

{rubric}

{text_context}

---

## Student Text

{text}

---

## Pre-Extracted Signals (VALIDATE your assessment against these)

**Evidence:**
- Evidence items detected: {evidence_count}
- Quote patterns found: {quote_count}

**Reasoning:**
- Cause-effect chains detected: {cause_effect_count}
- Comparison patterns detected: {comparison_count}
- Total reasoning chains: {total_chains}

**Argument Structure:**
- Counter-argument signals: {counter_signals}
- Synthesis markers: {has_synthesis}

**VALIDATION RULES:**
- If you assess evidence_quality as "paraphrased" or "specific" but evidence_count=0, reconsider
- If you assess dcceps_layer >= 3 but cause_effect_count=0, reconsider  
- If you assess has_counter_argument=true but counter_signals=0, reconsider
- These signals may miss some patterns, but 0 counts are strong indicators of absence

---

## Your Task

**CHARITABLY INTERPRET the student's argument.** 

1. **Determine Position** — What are they arguing? Look past errors to find the claim.
2. **Assess DCCEPS Layer** — What level of reasoning? Look for patterns, not keywords.
3. **Identify Themes** — Which themes do they engage with?
4. **Check Device Awareness** — Any literary devices mentioned?
5. **Score Reasoning Quality** — Do ideas connect logically?

---

Respond with JSON only:

{{
  "position": "hero|victim|transformation|both|unclear",
  "position_strength": "strong|moderate|implicit",
  "position_reasoning": "brief explanation",
  
  "dcceps_layer": 1-4,
  "dcceps_label": "Definition|Comparison|Cause-Effect|Problem-Solution",
  "dcceps_reasoning": "what reasoning patterns detected",
  
  "themes_identified": ["theme1", "theme2"],
  "devices_mentioned": ["device1"],
  "charitable_interpretation": "What the student is actually arguing",
  
  "sm1_score": 1.0-5.0,
  "sm2_score": 1.0-5.0,
  "sm3_score": 1.0-5.0,
  "ceiling": 4.5,
  "overall_score": 1.0-5.0,
  "total_points": 5.0-25.0,
  
  "evidence_quality": "specific|paraphrased|general|missing",
  "has_counter_argument": true/false,
  "has_synthesis": true/false,
  
  "feedback": {{
    "sm1": "what's working",
    "sm1_next": "next step",
    "sm2": "what's working",
    "sm2_next": "next step", 
    "sm3": "what's working",
    "sm3_next": "next step",
    "dcceps_guidance": "how to reach next layer",
    "stage1_integration": "weak|moderate|strong - note on device usage",
    "alignment_mode": "narrative|structure|voice",
    "alignment_mode_note": "observation about organization"
  }}
}}
"""


def validate_api_against_components(
    result: Dict,
    evidence_count: int,
    cause_effect_count: int,
    counter_signals: int,
    has_synthesis: bool,
    year_level: int
) -> Dict:
    """
    Hard validation: Override API assessments that contradict extracted components.
    
    Returns modified result dict with any corrections applied.
    """
    
    corrections = []
    
    # Validation 1: Evidence quality vs evidence count
    claimed_evidence = result.get('evidence_quality', 'missing')
    if claimed_evidence in ('specific', 'paraphrased') and evidence_count == 0:
        corrections.append(f"evidence_quality: {claimed_evidence} → missing (0 items detected)")
        result['evidence_quality'] = 'missing'
        result['sm1_score'] = min(result.get('sm1_score', 5.0), 2.5)
        result['ceiling'] = min(result.get('ceiling', 5.0), 3.0)
    
    # Validation 1b: Cap SM1 if no evidence detected (regardless of what API claims)
    if evidence_count == 0:
        if result.get('sm1_score', 0) > 2.5:
            corrections.append(f"sm1_score: {result['sm1_score']} → 2.5 (evidence_count=0)")
            result['sm1_score'] = 2.5
            result['ceiling'] = 3.0
        # Also fix the label if API got it wrong
        if result.get('evidence_quality') not in ('missing', 'general'):
            corrections.append(f"evidence_quality: {result.get('evidence_quality')} → missing (evidence_count=0)")
            result['evidence_quality'] = 'missing'
    
    # Validation 2: DCCEPS layer vs cause-effect chains
    claimed_layer = result.get('dcceps_layer', 1)
    if claimed_layer >= 3 and cause_effect_count == 0:
        corrections.append(f"dcceps_layer: {claimed_layer} → 2 (0 cause-effect chains detected)")
        result['dcceps_layer'] = 2
        result['dcceps_label'] = 'Comparison'
        # Recalculate SM2 with corrected layer
        result['sm2_score'] = score_dcceps_relative(2, year_level)
    
    # Validation 3: Counter-argument claim vs signals
    if result.get('has_counter_argument', False) and counter_signals == 0:
        corrections.append("has_counter_argument: true → false (0 signals detected)")
        result['has_counter_argument'] = False
    
    # Validation 4: SM scores cannot exceed ceiling
    ceiling = result.get('ceiling', 5.0)
    if result.get('sm2_score', 0) > ceiling:
        corrections.append(f"sm2_score: {result['sm2_score']} → {ceiling} (ceiling enforcement)")
        result['sm2_score'] = ceiling
    if result.get('sm3_score', 0) > ceiling:
        corrections.append(f"sm3_score: {result['sm3_score']} → {ceiling} (ceiling enforcement)")
        result['sm3_score'] = ceiling
    
    # Log corrections
    if corrections:
        print(f"  ⚠ Validation corrections applied:")
        for c in corrections:
            print(f"    - {c}")
    
    # Recalculate overall score
    sm1 = result.get('sm1_score', 3.0)
    sm2 = result.get('sm2_score', 2.5)
    sm3 = result.get('sm3_score', 2.5)
    result['overall_score'] = round((sm1 * 0.4) + (sm2 * 0.3) + (sm3 * 0.3), 2)
    result['total_points'] = round(result['overall_score'] * 5, 1)
    
    result['validation_corrections'] = corrections
    
    return result


def evaluate_thesis_with_api(
    text: str,
    components=None,
    api_key: Optional[str] = None,
    year_level: int = 8,
    kernel_path: Optional[str] = None,
    reasoning_path: Optional[str] = None
) -> Dict:
    """
    Evaluate thesis using Claude API with context injection.
    
    Args:
        text: Student's argumentative writing
        components: Pre-extracted ThesisComponents (optional, for context)
        api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
        year_level: Student year level (7-12, default: 8)
        kernel_path: Path to kernel JSON for context injection
        reasoning_path: Path to reasoning doc JSON for charitable interpretation
    
    Returns:
        Dict with position, dcceps_layer, scores, feedback
    """
    
    if Anthropic is None:
        raise ImportError("anthropic package required: pip install anthropic --break-system-packages")
    
    key = api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set. Set environment variable or pass api_key parameter.")
    
    # Load reasoning context if provided
    book_context = ""
    if reasoning_path:
        try:
            book_context = load_reasoning_context(reasoning_path)
            print(f"  ✓ Loaded reasoning context")
        except Exception as e:
            print(f"  ⚠ Could not load reasoning context: {e}")
    
    # Extract text context if kernel provided
    text_context = ""
    if kernel_path:
        try:
            context = extract_thesis_context(kernel_path)
            text_context = build_context_section(context)
            print(f"  ✓ Loaded context for: {context['title']}")
        except Exception as e:
            print(f"  ⚠ Could not load kernel context: {e}")
    
    # Extract component info for context (if provided)
    if components is not None:
        evidence_count = len(getattr(components, 'evidence_items', []))
        reasoning_types = list(getattr(components, 'reasoning_types', {}).keys())
        counter_signals = len(getattr(components, 'counter_arguments', []))
        has_synthesis = bool(getattr(components, 'synthesis', None))
        # Calculate detailed signal counts from components
        cause_effect_count = len(getattr(components, 'reasoning_types', {}).get('cause_effect', []))
        comparison_count = len(getattr(components, 'reasoning_types', {}).get('comparison', []))
        total_chains = len(getattr(components, 'reasoning_chains', []))
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
        # Fallback counts
        cause_effect_count = 1 if 'cause_effect' in reasoning_types else 0
        comparison_count = 1 if 'comparison' in reasoning_types else 0
        total_chains = len(reasoning_types)
    
    quote_count = len(re.findall(r'"[^"]{10,}"', text))  # Quotes with 10+ chars
    
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
        rubric=full_rubric + book_context,
        text_context=text_context,
        text=text,
        year_level=year_level,
        evidence_count=evidence_count,
        quote_count=quote_count,
        cause_effect_count=cause_effect_count,
        comparison_count=comparison_count,
        total_chains=total_chains,
        counter_signals=counter_signals,
        has_synthesis="Yes" if has_synthesis else "No"
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
    
    # SOFT ceiling enforcement (not hard)
    ceiling = result.get('ceiling', 5.0)
    # Only enforce if way over — evidence quality is soft for thesis
    if result.get('sm2_score', 0) > ceiling + 1.0:
        result['sm2_score'] = ceiling + 0.5
    if result.get('sm3_score', 0) > ceiling + 1.0:
        result['sm3_score'] = ceiling + 0.5
    
    # Post-API validation: Override SM2 with year-relative scoring
    detected_layer = result.get('dcceps_layer', 2)
    expected_sm2 = score_dcceps_relative(detected_layer, year_level)
    if abs(result.get('sm2_score', 0) - expected_sm2) > 0.5:
        print(f"  ⚠ Adjusting SM2: {result['sm2_score']} → {expected_sm2} (year-relative)")
        result['sm2_score'] = min(expected_sm2, ceiling)  # Still respect ceiling
    
    # Hard validation against extracted components
    result = validate_api_against_components(
        result=result,
        evidence_count=evidence_count,
        cause_effect_count=cause_effect_count,
        counter_signals=counter_signals,
        has_synthesis=has_synthesis,
        year_level=year_level
    )
    
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
