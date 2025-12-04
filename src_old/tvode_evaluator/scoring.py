"""
TVODE Scoring - SM1, SM2, SM3 score calculations

Based on v3.3/v3.4 rubric requirements.
"""

import re
from typing import Dict, List, Tuple

from .components import TVODEComponents


def score_sm1(components: TVODEComponents) -> Tuple[float, float]:
    """
    SM1: Component Presence + Detail Quality → Ceiling
    
    Returns: (sm1_score, ceiling)
    """
    
    # Count functional components
    has_topic = len(components.topics) > 0
    has_verb = (
        len(components.verb_tiers.get('tier_1', [])) > 0 or 
        len(components.verb_tiers.get('tier_2', [])) > 0
    )
    has_object = len(components.objects) > 0
    has_detail = len(components.details) > 0
    has_effect = (
        len(components.effect_tiers.get('tier_1', [])) > 0 or
        len(components.effect_tiers.get('tier_2', [])) > 0 or
        len(components.effect_tiers.get('tier_3', [])) > 0
    )
    
    present = sum([has_topic, has_verb, has_object, has_detail, has_effect])
    detail_score = components.detail_score
    
    # Lookup table from rubric
    if present == 5 and detail_score >= 5.0:
        return 5.0, 5.0
    elif present == 5 and detail_score >= 4.5:
        return 4.5, 4.5
    elif present == 5 and detail_score >= 4.0:
        return 4.0, 4.0
    elif present >= 4 and detail_score >= 4.0:
        return 3.5, 4.0
    elif present >= 4 or detail_score >= 3.0:
        return 3.0, 3.0
    elif present >= 3:
        return 2.5, 3.0
    elif present >= 2:
        return 2.0, 2.5
    else:
        return 1.5, 2.0


def score_sm2(text: str, components: TVODEComponents, ceiling: float) -> float:
    """
    SM2: Density Performance (analytical attempts + quality)
    """
    
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    # Count analytical attempts (only Tier 1-2 verbs)
    functional_verbs = set()
    functional_verbs.update(components.verb_tiers.get('tier_1', []))
    functional_verbs.update(components.verb_tiers.get('tier_2', []))
    
    analytical_count = sum(
        1 for s in sentences 
        if any(v in s.lower() for v in functional_verbs)
    )
    
    # Quality multiplier
    avg_verb = _calc_avg_tier(components.verb_tiers)
    avg_effect = _calc_avg_tier(components.effect_tiers)
    quality = (avg_verb + avg_effect) / 2
    
    # Adjusted insights
    insights = analytical_count * quality
    
    # Score
    if insights >= 4:
        raw = 5.0
    elif insights >= 3:
        raw = 4.0
    elif insights >= 2:
        raw = 3.0
    elif insights >= 1:
        raw = 2.5
    else:
        raw = 2.0
    
    return min(raw, ceiling)


def score_sm3(text: str, components: TVODEComponents, ceiling: float) -> float:
    """
    SM3: Cohesion Performance (connectors + grammar)
    """
    
    connector_count = sum(len(c) for c in components.connector_types.values())
    connector_variety = len(components.connector_types)
    
    # Variety bonus
    effective = connector_count + (connector_variety * 0.1)
    
    # Grammar errors
    errors = detect_grammar_errors(text)
    
    # Score
    if effective >= 3 and errors <= 2:
        raw = 5.0
    elif effective >= 2 and errors <= 3:
        raw = 4.0
    elif effective >= 1 and errors <= 4:
        raw = 3.0
    elif errors <= 5:
        raw = 2.5
    else:
        raw = 2.0
    
    return min(raw, ceiling)


def _calc_avg_tier(tier_dict: Dict[str, List]) -> float:
    """Calculate weighted average tier quality (1.0 = best)"""
    
    weights = {
        'tier_1': 1.0,
        'tier_2': 0.75,
        'tier_3': 0.5,
        'tier_4': 0.25,
        'tier_5': 0.0
    }
    
    total_weight = 0.0
    total_count = 0
    
    for tier, items in tier_dict.items():
        count = len(items)
        if count > 0:
            total_weight += weights.get(tier, 0.0) * count
            total_count += count
    
    return total_weight / total_count if total_count > 0 else 0.5


def detect_grammar_errors(text: str) -> int:
    """Detect common grammar errors"""
    
    errors = 0
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    # Subject-verb agreement
    agreement_patterns = [
        r'\b(?:description|narrator|character|theme|conflict)\s+are\b',
        r'\b(?:descriptions|narrators|characters|themes)\s+is\b',
        r'\b(?:he|she|it|this|that)\s+(?:have|are|were|leave|make)\b',
        r'\b(?:they|we|these|those)\s+(?:has|is|was|leaves|makes)\b',
        r'\bpoint of view.*?leave\b'
    ]
    
    for p in agreement_patterns:
        errors += len(re.findall(p, text, re.I))
    
    # Awkward phrasing
    awkward = [
        r'feel more deep in',
        r'make the reader to\s',
        r'makes reader\s',
    ]
    
    for p in awkward:
        errors += len(re.findall(p, text, re.I))
    
    # Short fragments
    for s in sentences:
        if len(s.split()) < 3 and s.lower() not in ['yes', 'no', 'okay']:
            errors += 1
    
    # Run-ons
    for s in sentences:
        if len(s.split()) > 35 and s.count(',') < 2:
            errors += 0.5
    
    return int(errors)
