"""
API-Based TVODE Evaluation

Uses Anthropic Claude API to evaluate student writing with semantic understanding.
Falls back to rule-based if API unavailable.
"""

import json
import os
import re
from typing import Dict, Optional
from anthropic import Anthropic

from .components import TVODEComponents


# Condensed rubric for prompt (keep under 1500 tokens)
RUBRIC_PROMPT = """
## TVODE Rubric v3.3 (Condensed)

### SM1: Component Presence (40% weight)
Assess: Are T-V-O-D-E components present? What is Detail quality?

**Detail Quality Levels - USE THESE EXAMPLES:**

VAGUE (ceiling 3.0):
- "careful language" (no specific text cited)
- "shows emotions" (general description)
- "Jonas is curious about things" (no quote, no specific moment)

SPECIFIC (ceiling 4.0):
- "Jonas searches for 'precise language'" (has quote but limited context)
- "takes apple home despite food-hoarding rules" (specific action, no quote)
- References to specific scenes without exact wording

PRECISE (ceiling 4.5-5.0):
- "he breathed again, feeling the sharp intake of frigid air" (exact quote with sensory detail)
- "when did we, in the past?" (exact dialogue quoted)
- "why don't we have snow?" (exact character question quoted)
- Any EXACT QUOTE from the text = at minimum SPECIFIC, usually PRECISE

**IMPORTANT:** If student includes direct quotes with quotation marks from the novel, their details are AT LEAST specific (4.0 ceiling), likely precise (4.5-5.0 ceiling). Do NOT score quotes as "vague".

**Scoring:**
- 5/5: All T-V-O-D-E components + precise quotes enabling clear interpretation
- 4-4.5/5: Four+ components + exact quotes present
- 3-3.5/5: T-V-O present but details are general descriptions (NO quotes)
- 2/5: Two components only
- 1/5: Mostly summary/description

### SM2: Density Performance (30% weight)
Assess: Given detail quality, how well did student maximize analytical insights?

**Effect Depth Dimensions:**
- READER RESPONSE: "makes reader question/feel/believe", "creates suspense/mystery"
- MEANING CREATION: "reveals how...", "shows us how...", "exposes...", "demonstrates that..."
- THEMATIC IMPACT: "reinforces theme of...", "reflects concern with...", "challenges the idea that..."

**Scoring (within SM1 ceiling):**
- 5.0/5: 3-4 insights across ALL THREE dimensions
- 4.0/5: 3-4 distinct insights (any combination)
- 3.0-3.5/5: 2-3 insights, may be repetitive or single dimension
- 2.0-2.5/5: 1-2 surface-level insights
- 1.0-1.5/5: Minimal analysis, plot summary

### SM3: Cohesion Performance (30% weight)
Assess: Given detail quality, how well are ideas connected?

**Key Question: Does grammar HINDER CLARITY or just have surface errors?**

Surface errors (don't heavily penalize):
- Wrong verb tense: "makes the reader had experienced" 
- Awkward phrasing: "feel more deep into"
- Agreement errors: "description are limited"
- IF THE MEANING IS STILL CLEAR, these are surface errors

Meaning-disrupting errors (penalize more heavily):
- Reader cannot follow the argument
- Ideas are incoherent or contradictory
- Sentences don't connect logically

**SM3 Scoring Scale (within SM1 ceiling):**

| Score | Connectors | Grammar |
|-------|------------|---------|
| **5.0** | 3+ types | No errors |
| **4.5** | 3+ types | 1-2 minor errors, meaning clear |
| **4.0** | 3+ types | Surface errors but meaning fully clear |
| **3.5** | 2-3 types | Some errors, meaning mostly clear |
| **3.0** | 2 types | Errors beginning to affect clarity |
| **2.5** | 1 type | Errors disrupt meaning |
| **2.0** | Few/none | Meaning unclear |

**IMPORTANT:** If student has 3+ connector types AND their argument is easy to follow, score 3.5-4.0 even with multiple surface errors. Only drop to 2.5 or below if you genuinely cannot understand their point.

**DO NOT count as grammar errors:**
- "n/a" markers (transcription artifacts)
- Repeated words like "limited limited" (handwriting corrections)
- "[UNCLEAR]" markers
- Garbled text from transcription issues

### Critical Rules
1. SM1 ceiling caps SM2 and SM3 - scores cannot exceed ceiling
2. Exact quotes from the text = SPECIFIC or PRECISE details (ceiling 4.0+)
3. SM3: Meaning clarity matters more than error count - clear meaning + surface errors = 4.0
4. Do NOT count transcription artifacts (n/a, repeated words, unclear markers) as grammar errors
"""


EVALUATION_PROMPT = """
You are evaluating a student's TVODE literary analysis. Apply the rubric precisely.

{rubric}

---

## Student Transcript

{transcript}

---

## Pre-Extracted Components (for reference)

Topics: {topics}
Verbs: {verbs}
Details: {details}
Effects: {effects}
Connectors: {connectors}

---

## Your Task

1. **Score SM1 (Component Presence + Detail Quality)**
   - Check: Does student include EXACT QUOTES from the text?
   - If YES (quotes in quotation marks): Details are SPECIFIC (4.0) or PRECISE (4.5-5.0)
   - If NO (only general descriptions): Details are VAGUE (3.0)
   - The ceiling you set here determines maximum SM2 and SM3 scores

2. **Score SM2 (Density Performance) WITHIN the ceiling**
   - Count distinct analytical insights (different claims, not restatements)
   - Check which dimensions: reader response, meaning creation, thematic impact
   - Score based on insight count and dimension coverage

3. **Score SM3 (Cohesion Performance) WITHIN the ceiling**
   - Count connector types (addition, contrast, cause-effect, exemplification)
   - Ask: "Can I follow this student's argument?" 
   - If YES (meaning clear): Score 3.5-4.0+ regardless of surface error count
   - If NO (meaning unclear): Score lower based on how much clarity is lost
   - Do NOT count transcription artifacts (n/a, repeated words) as errors
   - Surface errors with clear meaning = 4.0, not 2.5

4. **Generate feedback**
   - What IS working (positive framing)
   - ONE concrete next step
   - Specific examples from their text

---

## Output Format

Respond with ONLY valid JSON (no markdown, no explanation):

{{
  "sm1_score": <float 1.0-5.0>,
  "sm1_reasoning": "<one sentence explaining score>",
  "detail_quality": "<vague|specific|precise>",
  "ceiling": <float: 3.0 for vague, 4.0 for specific, 4.5-5.0 for precise>,
  
  "sm2_score": <float, must be <= ceiling>,
  "sm2_reasoning": "<one sentence explaining score>",
  "distinct_insights": <int>,
  "effect_dimensions": {{
    "reader_response": <bool - true if present>,
    "meaning_creation": <bool - true if present>,
    "thematic_impact": <bool - true if present>
  }},
  
  "sm3_score": <float - base on MEANING CLARITY not error count>,
  "sm3_reasoning": "<explain if meaning is clear despite errors>",
  "connector_types": <int count of distinct types>,
  "meaning_clear": <bool - can you follow the argument?>,
  "grammar_error_count": <int - surface errors only, not transcription artifacts>,
  "grammar_errors": ["<surface error 1>", "<surface error 2>"],
  
  "feedback": {{
    "sm1_current": "<what student did well>",
    "sm1_next": "<one concrete improvement>",
    "sm2_current": "<what student did well>",
    "sm2_next": "<one concrete improvement>",
    "sm3_current": "<what student did well>",
    "sm3_next": "<one concrete improvement>"
  }},
  
  "one_line_fix": "<highest-impact single edit, showing before → after>"
}}
"""


def evaluate_with_api(
    transcript_text: str,
    components: TVODEComponents,
    api_key: Optional[str] = None
) -> Dict:
    """
    Evaluate transcript using Claude API.
    
    Args:
        transcript_text: Raw student text
        components: Pre-extracted TVODE components
        api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
    
    Returns:
        Dict with scores, reasoning, and feedback
    """
    
    # Get API key
    key = api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    
    client = Anthropic(api_key=key)
    
    # Build prompt
    prompt = EVALUATION_PROMPT.format(
        rubric=RUBRIC_PROMPT,
        transcript=transcript_text,
        topics=', '.join(components.topics[:10]) if components.topics else 'None detected',
        verbs=', '.join(components.verbs[:10]) if components.verbs else 'None detected',
        details='; '.join(components.details[:5]) if components.details else 'None detected',
        effects='; '.join(components.effects[:3]) if components.effects else 'None detected',
        connectors=_format_connectors(components.connector_types)
    )
    
    # Call API
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Parse response
    response_text = response.content[0].text.strip()
    
    # Handle potential markdown wrapping
    if response_text.startswith('```'):
        response_text = response_text.split('```')[1]
        if response_text.startswith('json'):
            response_text = response_text[4:]
    
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse API response as JSON: {e}\nResponse: {response_text[:500]}")
    
    # NEW: Validate detail quality against actual quotes
    has_quotes = bool(re.search(r'"[^"]{10,}"', transcript_text))  # Quote with 10+ chars
    
    if has_quotes and result.get('detail_quality') == 'vague':
        # Override: student has quotes, can't be vague
        print("  ⚠ API marked details as 'vague' but quotes detected - adjusting to 'specific'")
        result['detail_quality'] = 'specific'
        result['ceiling'] = max(result.get('ceiling', 3.0), 4.0)
        result['sm1_score'] = max(result.get('sm1_score', 3.0), 4.0)
    
    # Validate ceiling logic
    ceiling = result.get('ceiling', 5.0)
    if result.get('sm2_score', 0) > ceiling:
        result['sm2_score'] = ceiling
    if result.get('sm3_score', 0) > ceiling:
        result['sm3_score'] = ceiling
    
    # Calculate overall
    sm1 = result.get('sm1_score', 3.0)
    sm2 = result.get('sm2_score', 2.5)
    sm3 = result.get('sm3_score', 2.5)
    result['overall_score'] = (sm1 * 0.4) + (sm2 * 0.3) + (sm3 * 0.3)
    result['total_points'] = result['overall_score'] * 5
    
    return result


def _format_connectors(connector_types: Dict) -> str:
    """Format connector types for prompt"""
    if not connector_types:
        return 'None detected'
    
    parts = []
    for ctype, conns in connector_types.items():
        parts.append(f"{ctype}: {', '.join(conns)}")
    return '; '.join(parts)

