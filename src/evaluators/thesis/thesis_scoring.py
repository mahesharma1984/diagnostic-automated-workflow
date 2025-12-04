"""
Thesis Scoring - Calculate thesis quality scores

Based on DCCEPS framework:
- SM1: Position Clarity + Evidence Quality (parallel to TVODE's Component Presence)
- SM2: Reasoning Depth (parallel to TVODE's Density Performance)
- SM3: Argument Coherence (parallel to TVODE's Cohesion Performance)
"""

import re
from typing import Tuple

from .thesis_components import ThesisComponents


def score_thesis_sm1(components: ThesisComponents, text: str = "") -> Tuple[float, float]:
    """
    SM1: Position Clarity + Evidence Quality → Ceiling
    
    Parallel to TVODE's Component Presence + Detail Quality
    
    Returns: (sm1_score, ceiling)
    """
    
    # Position clarity (0-2 points)
    position_points = 0.0
    if components.position != "unclear":
        position_points += 1.0
        if components.position_strength in ['strong', 'moderate']:
            position_points += 1.0
        elif components.position_strength == 'implicit':
            position_points += 0.5
    
    # Evidence quality (0-3 points)
    evidence_points = 0.0
    if components.evidence_quality == "specific":
        evidence_points = 3.0
    elif components.evidence_quality == "paraphrased":
        evidence_points = 2.0
    elif components.evidence_quality == "general":
        evidence_points = 1.0
    elif components.evidence_quality == "assertion":
        evidence_points = 0.5
    
    # Evidence QUANTITY bonus/penalty
    # Need multiple pieces of evidence for full credit
    evidence_count = len(components.evidence_items)
    if evidence_count < 2:
        evidence_points *= 0.7  # Penalty for single evidence
    elif evidence_count >= 4:
        evidence_points = min(3.0, evidence_points * 1.1)  # Bonus cap
    
    # Combined score (0-5)
    raw_score = position_points + evidence_points
    
    # Map to SM1 score and ceiling
    if raw_score >= 4.5:
        return 5.0, 5.0
    elif raw_score >= 4.0:
        return 4.5, 4.5
    elif raw_score >= 3.5:
        return 4.0, 4.0
    elif raw_score >= 3.0:
        return 3.5, 4.0
    elif raw_score >= 2.0:
        return 3.0, 3.0
    elif raw_score >= 1.0:
        return 2.0, 2.5
    else:
        return 1.5, 2.0


def score_thesis_sm2(components: ThesisComponents, text: str, ceiling: float) -> float:
    """
    SM2: Reasoning Depth
    
    Assesses DCCEPS layer reached + quality of reasoning chains
    
    Parallel to TVODE's Density Performance
    """
    
    # Base score from DCCEPS layer (1-4 maps to 2-5)
    layer_scores = {
        0: 1.5,  # No clear position
        1: 2.5,  # Definition only
        2: 3.5,  # Comparison
        3: 4.0,  # Cause-Effect (reduced from 4.5)
        4: 5.0   # Problem-Solution
    }
    
    base_score = layer_scores.get(components.dcceps_layer, 2.0)
    
    # Quality adjustments
    
    # Count UNIQUE reasoning chains (deduplicated)
    unique_chains = len(set(components.reasoning_chains))
    
    # Depth bonus: multiple distinct reasoning moves
    if unique_chains >= 4:
        depth_bonus = 0.5
    elif unique_chains >= 2:
        depth_bonus = 0.25
    else:
        depth_bonus = 0.0
    
    # Length consideration: very short responses can't reach full depth
    word_count = len(text.split())
    if word_count < 50:
        base_score = min(base_score, 3.0)  # Cap at 3.0 for very short
    elif word_count < 100:
        base_score = min(base_score, 4.0)  # Cap at 4.0 for short
    
    # Contradiction penalty: contradictory statements reduce score
    if _has_contradictions(text):
        base_score -= 0.5
    
    raw_score = base_score + depth_bonus
    
    return min(max(raw_score, 1.5), ceiling)


def _has_contradictions(text: str) -> bool:
    """Check for contradictory statements that undermine argument"""
    text_lower = text.lower()
    
    # Pattern: states X is Y, then says X is not Y
    contradiction_patterns = [
        (r'is\s+(?:a\s+)?victim', r'is\s+not\s+(?:really\s+)?(?:a\s+)?victim'),
        (r'is\s+(?:a\s+)?hero', r'is\s+not\s+(?:really\s+)?(?:a\s+)?hero'),
        (r'more\s+(?:of\s+a\s+)?victim', r'not\s+(?:really\s+)?(?:a\s+)?victim'),
        (r'more\s+(?:of\s+a\s+)?hero', r'not\s+(?:really\s+)?(?:a\s+)?hero'),
    ]
    
    for pos_pattern, neg_pattern in contradiction_patterns:
        if re.search(pos_pattern, text_lower) and re.search(neg_pattern, text_lower):
            # Check if it's a proper counter-argument (with "but", "however")
            if not re.search(r'\b(?:but|however|although|while)\b.*' + neg_pattern, text_lower):
                return True
    
    return False


def score_thesis_sm3(components: ThesisComponents, text: str, ceiling: float) -> float:
    """
    SM3: Argument Coherence
    
    Assesses:
    - Counter-argument acknowledgment
    - Synthesis quality
    - Overall argument flow
    
    Parallel to TVODE's Cohesion Performance
    """
    
    score = 2.0  # Base score
    
    # Counter-argument bonus (up to 1.0)
    if components.counter_score > 0:
        score += components.counter_score
    
    # Synthesis bonus (up to 1.0)
    if components.synthesis_score > 0:
        score += components.synthesis_score
    
    # Flow bonus - check for logical progression markers
    flow_markers = [
        r'\bfirst(?:ly)?\b',
        r'\bsecond(?:ly)?\b',
        r'\bthird(?:ly)?\b',
        r'\bfinally\b',
        r'\bfurthermore\b',
        r'\bmoreover\b',
        r'\bin\s+addition\b',
    ]
    
    text_lower = text.lower()
    flow_count = sum(1 for p in flow_markers if re.search(p, text_lower))
    
    if flow_count >= 3:
        score += 0.5
    elif flow_count >= 2:
        score += 0.25
    
    # Grammar penalty (simple check)
    errors = _detect_thesis_grammar_errors(text)
    if errors > 3:
        score -= 0.5
    elif errors > 5:
        score -= 1.0
    
    return min(max(score, 1.5), ceiling)


def _detect_thesis_grammar_errors(text: str) -> int:
    """Detect common grammar errors in argumentative writing"""
    
    errors = 0
    
    # Run-on sentences (very long without structure)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    for s in sentences:
        if len(s.split()) > 40 and s.count(',') < 2:
            errors += 1
    
    # Subject-verb agreement
    patterns = [
        r'\b(?:he|she|it|jonas)\s+(?:are|were|have)\b',
        r'\b(?:they|we)\s+(?:is|was|has)\b',
    ]
    for p in patterns:
        errors += len(re.findall(p, text, re.I))
    
    # Informal language in argument
    informal = [
        r'\bgonna\b',
        r'\bwanna\b',
        r'\bkinda\b',
        r'\bsorta\b',
    ]
    for p in informal:
        errors += len(re.findall(p, text, re.I))
    
    return errors


def calculate_overall_thesis_score(sm1: float, sm2: float, sm3: float) -> Tuple[float, float]:
    """
    Calculate overall thesis score
    
    Returns: (overall_score_0_5, total_points_0_25)
    """
    
    # Weighted average (same weights as TVODE)
    overall = (sm1 * 0.4) + (sm2 * 0.3) + (sm3 * 0.3)
    total_points = overall * 5
    
    return overall, total_points





