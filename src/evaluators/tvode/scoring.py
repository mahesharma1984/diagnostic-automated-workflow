"""
TVODE Scoring - SM1, SM2, SM3 score calculations

Based on v3.3/v3.4 rubric requirements.
"""

import re
from typing import Dict, List, Tuple, Set

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


def score_sm2(text: str, components: TVODEComponents, ceiling: float) -> Tuple[float, Dict[str, bool], int]:
    """
    SM2: Density Performance (analytical attempts + depth dimensions)
    
    Returns: (score, effect_dimensions, distinct_insights)
    """
    
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    text_lower = text.lower()
    
    # Count analytical attempts (only Tier 1-2 verbs)
    functional_verbs = set()
    functional_verbs.update(components.verb_tiers.get('tier_1', []))
    functional_verbs.update(components.verb_tiers.get('tier_2', []))
    
    # Track distinct insights (sentences with analytical verbs)
    distinct_insights = sum(
        1 for s in sentences 
        if any(v in s.lower() for v in functional_verbs)
    )
    
    # Detect effect dimensions
    effect_dimensions = _detect_effect_dimensions(text_lower, sentences)
    
    # Count dimensions present
    dimensions_present = sum([
        effect_dimensions['reader_response'],
        effect_dimensions['meaning_creation'],
        effect_dimensions['thematic_impact']
    ])
    
    # Score based on rubric logic
    if ceiling <= 3.0:
        # SM1 = 3 (vague details, ceiling = 3.0)
        if distinct_insights >= 2:
            raw = 3.0  # Maximum for ceiling
        elif distinct_insights >= 1:
            raw = 2.5
        else:
            raw = 1.5
    elif ceiling <= 4.0:
        # SM1 = 4 (specific details, ceiling = 4.0)
        if distinct_insights >= 3 and dimensions_present >= 2:
            raw = 4.0
        elif distinct_insights >= 2:
            raw = 3.5
        elif distinct_insights >= 1:
            raw = 2.5
        else:
            raw = 2.0
    else:
        # SM1 = 5 (precise details, ceiling = 5.0)
        if distinct_insights >= 3 and dimensions_present == 3:
            raw = 5.0  # All three dimensions
        elif distinct_insights >= 3 and dimensions_present == 2:
            raw = 4.5  # Two dimensions
        elif distinct_insights >= 3:
            raw = 4.0
        elif distinct_insights >= 2:
            raw = 3.5
        else:
            raw = 3.0
    
    return min(raw, ceiling), effect_dimensions, distinct_insights


def _detect_effect_dimensions(text_lower: str, sentences: List[str]) -> Dict[str, bool]:
    """
    Detect which effect depth dimensions are present:
    - reader_response: How device affects reader
    - meaning_creation: What device reveals about text/characters
    - thematic_impact: How device connects to broader themes
    """
    
    dimensions = {
        'reader_response': False,
        'meaning_creation': False,
        'thematic_impact': False
    }
    
    # Reader Response patterns
    reader_patterns = [
        r'makes?\s+(?:the\s+)?reader\s+(?:question|feel|believe|think|realize|understand)',
        r'creates?\s+(?:suspense|mystery|tension|engagement)',
        r'engages?\s+(?:the\s+)?reader',
        r'readers?\s+(?:to\s+)?(?:question|feel|believe|think)'
    ]
    
    # Meaning Creation patterns
    meaning_patterns = [
        r'reveals?\s+how',
        r'exposes?\s+(?:the\s+)?(?:gap|truth|reality)',
        r'demonstrates?\s+that',
        r'shows?\s+us\s+how',
        r'indicates?\s+that',
        r'suggests?\s+that'
    ]
    
    # Thematic Impact patterns
    thematic_patterns = [
        r'reinforces?\s+(?:the\s+)?theme\s+of',
        r'challenges?\s+(?:the\s+)?(?:idea|notion|concept)\s+that',
        r'reflects?\s+(?:the\s+)?(?:novel\'?s|text\'?s|story\'?s)\s+concern\s+with',
        r'connects?\s+to\s+(?:the\s+)?(?:theme|broader\s+theme)',
        r'illustrates?\s+(?:the\s+)?(?:theme|central\s+idea)'
    ]
    
    # Check each sentence
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        # Check reader response
        if not dimensions['reader_response']:
            if any(re.search(p, sentence_lower) for p in reader_patterns):
                dimensions['reader_response'] = True
        
        # Check meaning creation
        if not dimensions['meaning_creation']:
            if any(re.search(p, sentence_lower) for p in meaning_patterns):
                dimensions['meaning_creation'] = True
        
        # Check thematic impact
        if not dimensions['thematic_impact']:
            if any(re.search(p, sentence_lower) for p in thematic_patterns):
                dimensions['thematic_impact'] = True
    
    return dimensions


def score_sm3(text: str, components: TVODEComponents, ceiling: float) -> Tuple[float, int, List[str]]:
    """
    SM3: Cohesion Performance (connectors + grammar error bands)
    
    Returns: (score, grammar_error_count, grammar_errors)
    """
    
    connector_count = sum(len(c) for c in components.connector_types.values())
    connector_variety = len(components.connector_types)
    
    # Grammar errors with detailed tracking
    grammar_error_count, grammar_errors = detect_grammar_errors_detailed(text)
    
    # Apply grammar error bands (penalties from ceiling)
    max_score = ceiling
    
    if grammar_error_count >= 6:
        penalty = 1.5
    elif grammar_error_count >= 4:
        penalty = 1.0
    elif grammar_error_count >= 2:
        penalty = 0.5
    else:
        penalty = 0.0
    
    # Base score from connectors (within ceiling)
    if ceiling <= 3.0:
        # SM1 = 3 (vague details, ceiling = 3.0)
        if connector_variety >= 2 and grammar_error_count <= 2:
            base = 3.0  # Maximum for ceiling
        elif connector_variety >= 1 and grammar_error_count <= 3:
            base = 2.5
        else:
            base = 1.5
    elif ceiling <= 4.0:
        # SM1 = 4 (specific details, ceiling = 4.0)
        if connector_variety >= 3 and grammar_error_count <= 1:
            base = 4.0
        elif connector_variety >= 3 and grammar_error_count <= 3:
            base = 3.5
        elif connector_variety >= 2 and grammar_error_count <= 3:
            base = 3.0
        elif connector_variety >= 1:
            base = 2.5
        else:
            base = 2.0
    else:
        # SM1 = 5 (precise details, ceiling = 5.0)
        if connector_variety >= 3 and grammar_error_count == 0:
            base = 5.0
        elif connector_variety >= 3 and grammar_error_count <= 1:
            base = 4.5
        elif connector_variety >= 2 and grammar_error_count <= 3:
            base = 4.0
        else:
            base = 3.5
    
    # Apply grammar penalty
    raw = max(1.0, base - penalty)
    
    return min(raw, ceiling), grammar_error_count, grammar_errors


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
    """Detect common grammar errors (backward compatibility)"""
    count, _ = detect_grammar_errors_detailed(text)
    return count


def detect_grammar_errors_detailed(text: str) -> Tuple[int, List[str]]:
    """
    Detect common grammar errors with detailed tracking
    
    Returns: (error_count, list_of_error_descriptions)
    """
    
    errors = []
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    text_lower = text.lower()
    
    # Subject-verb agreement
    agreement_patterns = [
        (r'\b(?:description|narrator|character|theme|conflict)\s+are\b', 'subject-verb agreement'),
        (r'\b(?:descriptions|narrators|characters|themes)\s+is\b', 'subject-verb agreement'),
        (r'\b(?:he|she|it|this|that)\s+(?:have|are|were|leave|make)\b', 'subject-verb agreement'),
        (r'\b(?:they|we|these|those)\s+(?:has|is|was|leaves|makes)\b', 'subject-verb agreement'),
        (r'\bpoint of view.*?leave\b', 'subject-verb agreement'),
    ]
    
    for pattern, error_type in agreement_patterns:
        matches = re.findall(pattern, text_lower, re.I)
        for _ in matches:
            errors.append(error_type)
    
    # Tense inconsistency
    tense_patterns = [
        (r'makes?\s+(?:the\s+)?reader\s+had\s+', 'tense inconsistency'),
        (r'makes?\s+(?:the\s+)?reader\s+was\s+', 'tense inconsistency'),
    ]
    
    for pattern, error_type in tense_patterns:
        matches = re.findall(pattern, text_lower, re.I)
        for _ in matches:
            errors.append(error_type)
    
    # Awkward phrasing
    awkward_patterns = [
        (r'feel more deep (?:into|in)', 'awkward phrasing'),
        (r'make the reader to\s', 'awkward phrasing'),
        (r'makes reader\s', 'awkward phrasing'),
        (r'as an result', 'incorrect word form'),
    ]
    
    for pattern, error_type in awkward_patterns:
        matches = re.findall(pattern, text_lower, re.I)
        for _ in matches:
            errors.append(error_type)
    
    # Missing/wrong articles or prepositions (common patterns)
    article_patterns = [
        (r'\b(?:in|on|at|for|with|by)\s+(?:the|a|an)\s+(?:the|a|an)\b', 'missing/wrong article'),
    ]
    
    for pattern, error_type in article_patterns:
        matches = re.findall(pattern, text_lower, re.I)
        for _ in matches:
            errors.append(error_type)
    
    # Short fragments (but exclude transcription artifacts)
    for s in sentences:
        if len(s.split()) < 3 and s.lower() not in ['yes', 'no', 'okay', 'n/a', 'na']:
            # Check if it's a transcription artifact
            if not re.search(r'\b(?:n/a|unclear|illegible)\b', s.lower()):
                errors.append('fragment')
    
    # Run-ons
    for s in sentences:
        if len(s.split()) > 35 and s.count(',') < 2:
            errors.append('run-on sentence')
    
    return len(errors), errors
