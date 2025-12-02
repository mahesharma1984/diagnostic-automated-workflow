"""
Thesis Components - Extract PERCS from text
(Position, Evidence, Reasoning, Counter-argument, Synthesis)

This module handles all text analysis for thesis/argument extraction.
Parallel to TVODE's components.py but focused on argumentative structure.
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from .thesis_taxonomies import (
    POSITION_MARKERS, EVIDENCE_TYPES, REASONING_PATTERNS,
    COUNTER_ARGUMENT_SIGNALS, SYNTHESIS_MARKERS, DCCEPS_LAYERS
)


@dataclass
class ThesisComponents:
    """Extracted thesis/argument components from student writing"""
    
    # Core components (parallel to TVODE)
    position: str  # The stance taken (hero/victim/etc.)
    position_strength: str  # "strong", "moderate", "hedged", "implicit", "missing"
    evidence_items: List[str]  # List of evidence used
    evidence_quality: str  # "specific", "paraphrased", "general", "assertion"
    reasoning_chains: List[str]  # Logical connections made
    counter_arguments: List[str]  # Acknowledgment of other side
    synthesis: str  # Concluding/weighing statement
    
    # DCCEPS layer tracking
    dcceps_layer: int  # 1=Definition, 2=Comparison, 3=Cause-Effect, 4=Problem-Solution
    dcceps_label: str
    
    # Quality scores (0-1 scale)
    position_score: float = 0.0
    evidence_score: float = 0.0
    reasoning_score: float = 0.0
    counter_score: float = 0.0
    synthesis_score: float = 0.0
    
    # Enhanced tracking
    evidence_types: Dict[str, List[str]] = field(default_factory=dict)
    reasoning_types: Dict[str, List[str]] = field(default_factory=dict)


def extract_thesis_components(text: str) -> ThesisComponents:
    """Extract all thesis/argument components from student writing"""
    
    text_lower = text.lower()
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    # Extract each component type
    position, position_strength, position_score = _extract_position(text_lower)
    evidence_items, evidence_types, evidence_quality, evidence_score = _extract_evidence(text, sentences)
    reasoning_chains, reasoning_types, reasoning_score = _extract_reasoning(text_lower, sentences)
    counter_arguments, counter_score = _extract_counter_arguments(text_lower, sentences)
    synthesis, synthesis_score = _extract_synthesis(text_lower, sentences)
    
    # Determine DCCEPS layer
    dcceps_layer, dcceps_label = _assess_dcceps_layer(
        position_strength, evidence_quality, reasoning_types, 
        counter_arguments, synthesis
    )
    
    return ThesisComponents(
        position=position,
        position_strength=position_strength,
        evidence_items=evidence_items,
        evidence_quality=evidence_quality,
        reasoning_chains=reasoning_chains,
        counter_arguments=counter_arguments,
        synthesis=synthesis,
        dcceps_layer=dcceps_layer,
        dcceps_label=dcceps_label,
        position_score=position_score,
        evidence_score=evidence_score,
        reasoning_score=reasoning_score,
        counter_score=counter_score,
        synthesis_score=synthesis_score,
        evidence_types=evidence_types,
        reasoning_types=reasoning_types
    )


def _extract_position(text_lower: str) -> Tuple[str, str, float]:
    """
    Extract the position/stance taken
    
    Returns: (position_text, strength_label, score)
    """
    
    # First, identify what position is taken
    position = "unclear"
    
    # Check for hero/victim stance
    hero_patterns = [
        r'(?:is|more\s+(?:of\s+)?a)\s+hero',
        r'hero\s+(?:rather|instead)',
        r'(?:believe|think|feel).*hero',
    ]
    victim_patterns = [
        r'(?:is|more\s+(?:of\s+)?a)\s+victim',
        r'victim\s+(?:rather|instead)',
        r'(?:believe|think|feel).*victim',
    ]
    
    hero_count = sum(1 for p in hero_patterns if re.search(p, text_lower))
    victim_count = sum(1 for p in victim_patterns if re.search(p, text_lower))
    
    if hero_count > victim_count:
        position = "hero"
    elif victim_count > hero_count:
        position = "victim"
    elif hero_count > 0 and victim_count > 0:
        position = "both_acknowledged"
    
    # Assess strength of stance
    strength = "missing"
    score = 0.0
    
    for strength_type, data in POSITION_MARKERS.items():
        for pattern in data['patterns']:
            if re.search(pattern, text_lower):
                if data['weight'] > score:
                    strength = strength_type.replace('_stance', '')
                    score = data['weight']
    
    return position, strength, score


def _extract_evidence(text: str, sentences: List[str]) -> Tuple[List[str], Dict[str, List[str]], str, float]:
    """
    Extract evidence items with type classification
    
    Returns: (evidence_list, types_dict, quality_label, score)
    """
    
    evidence_items = []
    evidence_types = {
        'specific_textual': [],
        'paraphrased': [],
        'general_reference': [],
        'assertion_only': []
    }
    
    text_lower = text.lower()
    total_score = 0.0
    
    # First, extract quoted text (strongest evidence)
    quotes = re.findall(r'"([^"]+)"', text)
    for q in quotes:
        if len(q) > 3:  # Meaningful quotes only
            evidence_items.append(q)
            evidence_types['specific_textual'].append(q)
            total_score += 1.0
    
    # Then check for other evidence patterns
    for ev_type, data in EVIDENCE_TYPES.items():
        for pattern in data['patterns']:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    if isinstance(match, str) and len(match) > 10:  # Require more substance
                        # Avoid duplicates with quotes
                        if match not in [q.lower() for q in quotes]:
                            evidence_items.append(match)
                            evidence_types[ev_type].append(match)
                            total_score += data['weight']
    
    # Determine overall quality based on BEST evidence present
    specific_count = len(evidence_types['specific_textual'])
    paraphrased_count = len(evidence_types['paraphrased'])
    general_count = len(evidence_types['general_reference'])
    
    # Quality requires MULTIPLE good pieces
    if specific_count >= 2:
        quality = "specific"
    elif specific_count >= 1 and paraphrased_count >= 1:
        quality = "specific"  # One quote + one paraphrase = specific
    elif specific_count == 1:
        quality = "paraphrased"  # Single quote = paraphrased level
    elif paraphrased_count >= 2:
        quality = "paraphrased"
    elif paraphrased_count >= 1 or general_count >= 2:
        quality = "general"
    elif evidence_types['assertion_only']:
        quality = "assertion"
    else:
        quality = "missing"
    
    # Normalize score (need more evidence for full credit)
    normalized_score = min(1.0, total_score / 4.0)  # 4 pieces of good evidence = max
    
    return evidence_items, evidence_types, quality, normalized_score


def _extract_reasoning(text_lower: str, sentences: List[str]) -> Tuple[List[str], Dict[str, List[str]], float]:
    """
    Extract reasoning chains with type classification
    
    Returns: (reasoning_list, types_dict, score)
    """
    
    reasoning_chains = []
    reasoning_types = {
        'cause_effect': [],
        'comparison': [],
        'elaboration': [],
        'definition': []
    }
    
    total_score = 0.0
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        for r_type, data in REASONING_PATTERNS.items():
            for pattern in data['patterns']:
                if re.search(pattern, sentence_lower):
                    reasoning_chains.append(sentence)
                    reasoning_types[r_type].append(sentence)
                    total_score += data['weight']
                    break  # Only count once per sentence
    
    # Normalize score
    normalized_score = min(1.0, total_score / 3.0)  # 3 good reasoning moves = max
    
    return reasoning_chains, reasoning_types, normalized_score


def _extract_counter_arguments(text_lower: str, sentences: List[str]) -> Tuple[List[str], float]:
    """
    Extract counter-argument acknowledgments
    
    Returns: (counter_list, score)
    """
    
    counter_arguments = []
    total_score = 0.0
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        for ca_type, data in COUNTER_ARGUMENT_SIGNALS.items():
            for pattern in data['patterns']:
                if re.search(pattern, sentence_lower):
                    counter_arguments.append(sentence)
                    total_score += data['weight']
                    break
    
    # Normalize (1 good counter-acknowledgment is sufficient for basic score)
    normalized_score = min(1.0, total_score)
    
    return counter_arguments, normalized_score


def _extract_synthesis(text_lower: str, sentences: List[str]) -> Tuple[str, float]:
    """
    Extract synthesis/conclusion statement
    
    Returns: (synthesis_text, score)
    """
    
    synthesis = ""
    score = 0.0
    
    # Check last 3 sentences for synthesis markers
    final_sentences = sentences[-3:] if len(sentences) >= 3 else sentences
    
    for sentence in final_sentences:
        sentence_lower = sentence.lower()
        
        for s_type, data in SYNTHESIS_MARKERS.items():
            for pattern in data['patterns']:
                if re.search(pattern, sentence_lower):
                    if data['weight'] > score:
                        synthesis = sentence
                        score = data['weight']
    
    return synthesis, score


def _assess_dcceps_layer(
    position_strength: str,
    evidence_quality: str,
    reasoning_types: Dict[str, List[str]],
    counter_arguments: List[str],
    synthesis: str
) -> Tuple[int, str]:
    """
    Determine which DCCEPS layer the argument reaches
    
    Returns: (layer_number, layer_label)
    
    Layers:
    1 = Definition only (just identifies position)
    2 = Comparison (distinguishes between alternatives)
    3 = Cause-Effect (shows HOW evidence supports position)
    4 = Problem-Solution (frames purpose/function)
    """
    
    # Layer 4: Problem-Solution
    # Requires cause-effect reasoning + counter-argument + synthesis
    has_cause_effect = len(reasoning_types.get('cause_effect', [])) >= 2
    has_counter = len(counter_arguments) > 0
    has_synthesis = bool(synthesis)
    
    if has_cause_effect and has_counter and has_synthesis:
        return 4, "Problem-Solution"
    
    # Layer 3: Cause-Effect
    # Requires cause-effect reasoning explaining WHY evidence supports position
    if has_cause_effect:
        return 3, "Cause-Effect"
    
    # Layer 2: Comparison
    # Requires comparison reasoning (more than, rather than, etc.)
    has_comparison = len(reasoning_types.get('comparison', [])) > 0
    if has_comparison:
        return 2, "Comparison"
    
    # Layer 1: Definition
    # Just states position with or without evidence
    if position_strength != "missing":
        return 1, "Definition"
    
    return 0, "No Clear Position"

