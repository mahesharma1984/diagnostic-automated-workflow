"""
TVODE Components - Extract Topic, Verb, Object, Detail, Effect from text

This module handles all text analysis for component extraction.
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from .taxonomies import (
    VERB_LOOKUP, VERB_TIERS, EFFECT_TIERS, 
    CONNECTOR_TYPES, LITERARY_TOPICS
)


@dataclass
class TVODEComponents:
    """Extracted TVODE components from student writing"""
    topics: List[str]
    verbs: List[str]
    objects: List[str]
    details: List[str]
    effects: List[str]
    detail_quality: str  # "missing", "vague", "specific", "precise"
    
    # Enhanced tracking
    verb_tiers: Dict[str, List[str]] = field(default_factory=dict)
    effect_tiers: Dict[str, List[str]] = field(default_factory=dict)
    connector_types: Dict[str, List[str]] = field(default_factory=dict)
    detail_score: float = 0.0
    verb_quality_score: float = 0.0
    effect_quality_score: float = 0.0


def extract_components(text: str) -> TVODEComponents:
    """Extract all TVODE components from transcript text"""
    
    text_lower = text.lower()
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    # Extract each component type
    topics = _extract_topics(text_lower, sentences)
    verbs, verb_tiers, verb_quality = _extract_verbs(text_lower)
    objects = _extract_objects(text_lower, sentences)
    details = _extract_details(text)
    effects, effect_tiers, effect_quality = _extract_effects(sentences)
    connector_types = _extract_connectors(text_lower)
    
    # Assess detail quality
    detail_quality, detail_score = _assess_detail_quality(details, text)
    
    return TVODEComponents(
        topics=topics,
        verbs=verbs,
        objects=objects,
        details=details,
        effects=effects,
        detail_quality=detail_quality,
        verb_tiers=verb_tiers,
        effect_tiers=effect_tiers,
        connector_types=connector_types,
        detail_score=detail_score,
        verb_quality_score=verb_quality,
        effect_quality_score=effect_quality
    )


def _extract_topics(text_lower: str, sentences: List[str]) -> List[str]:
    """Extract Topic components (literary devices/concepts being analyzed)"""
    topics = []
    
    # Pattern 1: Known literary devices/concepts
    for topic in LITERARY_TOPICS:
        if topic in text_lower:
            topics.append(topic)
    
    # Pattern 2: Character names (capitalized words)
    for sentence in sentences:
        for word in sentence.split():
            if word and word[0].isupper() and len(word) > 2:
                if word.lower() not in ['the', 'this', 'that', 'chapter', 'in', 'and', 'for']:
                    topics.append(word)
    
    return list(set(topics))


def _extract_verbs(text_lower: str) -> Tuple[List[str], Dict[str, List[str]], float]:
    """Extract analytical verbs with tier classification"""
    verbs = []
    verb_tiers = {'tier_1': [], 'tier_2': [], 'tier_3': []}
    total_score = 0.0
    
    for verb, (tier, weight, label) in VERB_LOOKUP.items():
        if verb in text_lower:
            verbs.append(verb)
            verb_tiers[tier].append(verb)
            total_score += weight
    
    return list(set(verbs)), verb_tiers, total_score


def _extract_objects(text_lower: str, sentences: List[str]) -> List[str]:
    """Extract Objects (what's affected by the analysis)"""
    objects = []
    
    # Pattern: "make/create the reader [verb]"
    reader_patterns = [
        r'(?:make|makes|create|creates|cause|causes)\s+(?:the\s+)?readers?\s+(\w+)',
        r'readers?\s+(?:to\s+)?(\w+)',
        r'(?:believe|question|understand|feel|think|realize)\s+(\w+)'
    ]
    
    for pattern in reader_patterns:
        for match in re.finditer(pattern, text_lower):
            if match.group(1):
                objects.append(match.group(1))
    
    # Pattern: nouns after analytical verbs
    for sentence in sentences:
        for verb in VERB_LOOKUP.keys():
            if verb in sentence.lower():
                parts = sentence.lower().split(verb)
                if len(parts) > 1:
                    words = parts[1].split()[:5]
                    objects.extend([w for w in words if len(w) > 3])
    
    return list(set(objects))


def _extract_details(text: str) -> List[str]:
    """Extract Details (textual evidence/quotes)"""
    details = []
    
    # Pattern 1: Quoted text
    quotes = re.findall(r'"([^"]+)"', text)
    details.extend(quotes)
    
    # Pattern 2: Phrases after contextual words
    detail_patterns = [
        r'when\s+([^,\.]+)',
        r'through\s+([^,\.]+)',
        r'by\s+([^,\.]+)',
        r'with\s+([^,\.]+)',
        r'since\s+([^,\.]+)',
        r'after\s+([^,\.]+)'
    ]
    
    for pattern in detail_patterns:
        for match in re.finditer(pattern, text.lower()):
            if match.group(1):
                details.append(match.group(1).strip())
    
    return details


def _extract_effects(sentences: List[str]) -> Tuple[List[str], Dict[str, List[str]], float]:
    """Extract Effects with tier classification"""
    effects = []
    effect_tiers = {'tier_1': [], 'tier_2': [], 'tier_3': [], 'tier_4': [], 'tier_5': []}
    total_score = 0.0
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        # Check each tier from highest to lowest
        for tier_name, tier_data in EFFECT_TIERS.items():
            matched = False
            for pattern in tier_data['patterns']:
                if re.search(pattern, sentence_lower):
                    effects.append(sentence.strip())
                    effect_tiers[tier_name].append(sentence.strip())
                    total_score += tier_data['weight']
                    matched = True
                    break
            if matched:
                break
    
    return effects, effect_tiers, total_score


def _extract_connectors(text_lower: str) -> Dict[str, List[str]]:
    """Extract connectors classified by function"""
    connector_types = {}
    
    for func_type, connectors in CONNECTOR_TYPES.items():
        found = [conn for conn in connectors if conn in text_lower]
        if found:
            connector_types[func_type] = found
    
    return connector_types


# ==================== DETAIL QUALITY ASSESSMENT ====================

def _assess_detail_quality(details: List[str], text: str) -> Tuple[str, float]:
    """
    Assess detail quality using decision tree
    
    Returns: (quality_label, numeric_score)
    - 5.0: precise (quote + attribution + 4 context elements)
    - 4.5-4.75: precise (quote + attribution + 2-3 context)
    - 4.0-4.25: specific (quote with some context)
    - 3.0: vague (general descriptions)
    - 2.0: missing
    """
    
    if not details:
        return "missing", 2.0
    
    # Check for direct quotes
    quotes = re.findall(r'"([^"]+)"', text)
    
    if not quotes:
        # Paraphrase specificity check
        if _can_visualize_moment(text):
            return "specific", 4.0
        else:
            return "vague", 3.0
    
    # Has quotes - check for attribution
    has_attribution = bool(re.search(r'(?:p\.|page)\s*\d+|chapter\s+\d+', text, re.I))
    
    if not has_attribution:
        return "specific", 4.0
    
    # Count contextual elements
    score = 4.0
    if _explains_when(text): score += 0.25
    if _explains_why(text): score += 0.25
    if _explains_how(text): score += 0.25
    if _explains_what_reveals(text): score += 0.25
    
    if score >= 4.75:
        return "precise", 5.0
    elif score >= 4.25:
        return "precise", score
    else:
        return "specific", score


def _can_visualize_moment(text: str) -> bool:
    """Check if text has enough concrete detail to visualize"""
    markers = [
        r'\b(?:eyes|face|hands|voice|body|snow|air|cold|warm|light|dark)\b',
        r'\b(?:walked|ran|felt|saw|heard|touched|breathed|looked)\b',
        r'\b(?:slowly|quickly|suddenly|carefully|gently|sharply)\b',
    ]
    count = sum(1 for p in markers if re.search(p, text.lower()))
    return count >= 2


def _explains_when(text: str) -> bool:
    """Check for temporal context"""
    patterns = [
        r'(?:when|after|before|during|while)\s+\w+',
        r'(?:in|at)\s+(?:chapter|page|the\s+beginning|the\s+end)',
    ]
    return any(re.search(p, text.lower()) for p in patterns)


def _explains_why(text: str) -> bool:
    """Check for causal explanation"""
    patterns = [
        r'(?:because|since|due\s+to|as\s+a\s+result)',
        r'(?:to|in\s+order\s+to)\s+\w+',
    ]
    return any(re.search(p, text.lower()) for p in patterns)


def _explains_how(text: str) -> bool:
    """Check for mechanism explanation"""
    patterns = [
        r'(?:by|through|via|using)\s+\w+',
        r'(?:with|without)\s+\w+',
    ]
    return any(re.search(p, text.lower()) for p in patterns)


def _explains_what_reveals(text: str) -> bool:
    """Check for interpretive connection"""
    patterns = [
        r'(?:which|that|this)\s+(?:shows|reveals|demonstrates|suggests|indicates)',
        r'(?:revealing|showing|demonstrating)\s+(?:how|that|why)',
    ]
    return any(re.search(p, text.lower()) for p in patterns)
