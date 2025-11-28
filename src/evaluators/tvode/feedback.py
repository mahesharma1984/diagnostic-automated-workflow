"""
TVODE Feedback Generation

Generates contextualized feedback for each sub-metric.
Uses device context from kernel when available.
"""

import re
from typing import Dict, List, Optional

from .components import TVODEComponents, _explains_what_reveals
from .device_context import DeviceContext


def generate_feedback(
    components: TVODEComponents,
    sm1: float, sm2: float, sm3: float,
    text: str,
    device_ctx: DeviceContext,
    detected_device: Optional[str]
) -> Dict[str, str]:
    """
    Generate feedback for all three sub-metrics
    
    Args:
        components: Extracted TVODE components
        sm1, sm2, sm3: Scores
        text: Original student text
        device_ctx: Device context manager (has kernel data)
        detected_device: Name of detected device (or None)
    
    Returns:
        Dict with sm1, sm1_next, sm2, sm2_next, sm3, sm3_next
    """
    
    feedback = {}
    
    # Get device function if available
    device_function = ""
    if detected_device:
        device_function = device_ctx.get_function(detected_device)
    
    # Generate each section
    feedback.update(_generate_sm1_feedback(components, text, device_function))
    feedback.update(_generate_sm2_feedback(components, text, detected_device, device_function))
    feedback.update(_generate_sm3_feedback(components, text))
    
    return feedback


def _generate_sm1_feedback(
    components: TVODEComponents, 
    text: str,
    device_function: str
) -> Dict[str, str]:
    """Generate SM1 (Component Presence) feedback"""
    
    # What's present
    present = []
    if components.topics: present.append("Topic")
    if components.objects: present.append("Object")
    if components.details: present.append("Detail")
    
    sm1 = f"You have {', '.join(present)} components present. "
    sm1 += f"Your Details are {components.detail_quality} ({components.detail_score:.2f}/5)."
    
    # Next steps
    next_steps = []
    
    # Detail quality guidance
    if components.detail_score < 4.0:
        has_quotes = bool(re.search(r'"[^"]+"', text))
        has_attribution = bool(re.search(r'(?:p\.|page)\s*\d+|chapter\s+\d+', text, re.I))
        
        needs = []
        if not has_quotes:
            needs.append("add quotation marks around exact text")
        if not has_attribution:
            needs.append("add chapter/page reference")
        if not _explains_what_reveals(text):
            needs.append("add 'which reveals...' to show significance")
        
        if needs:
            next_steps.append(f"Transform details by: {', '.join(needs)}")
    
    # Verb tier guidance
    tier1 = components.verb_tiers.get('tier_1', [])
    tier2 = components.verb_tiers.get('tier_2', [])
    tier3 = components.verb_tiers.get('tier_3', [])
    
    if not tier1 and not tier2:
        if tier3:
            examples = ', '.join(tier3[:5])
            guidance = f"Try using Tier 1 verbs (reveals, creates, exposes, challenges) instead of Tier 3 verbs ({examples})"
            next_steps.append(guidance)
        else:
            next_steps.append("Use analytical verbs like reveals, creates, exposes, challenges")
    
    sm1_next = ". ".join(next_steps) + "." if next_steps else "Continue developing specific textual details."
    
    return {'sm1': sm1, 'sm1_next': sm1_next}


def _generate_sm2_feedback(
    components: TVODEComponents,
    text: str,
    detected_device: Optional[str],
    device_function: str
) -> Dict[str, str]:
    """Generate SM2 (Density Performance) feedback"""
    
    # Count analytical attempts
    sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
    functional_verbs = set()
    functional_verbs.update(components.verb_tiers.get('tier_1', []))
    functional_verbs.update(components.verb_tiers.get('tier_2', []))
    
    count = sum(1 for s in sentences if any(v in s.lower() for v in functional_verbs))
    
    sm2 = f"You make {count} analytical attempts. "
    sm2 += "Your effects focus on reader engagement."
    
    # Next steps
    next_steps = []
    
    if count < 3:
        next_steps.append("Build more distinct insights - each detail should unlock a DIFFERENT analytical point")
    
    # Effect tier guidance
    tier1_effects = components.effect_tiers.get('tier_1', [])
    tier2_effects = components.effect_tiers.get('tier_2', [])
    
    if not tier1_effects and not tier2_effects:
        # Use detected device name if available, otherwise generic
        device_name = detected_device.title() if detected_device else "the device"
        next_steps.append(
            f"Push toward meaning production (Tier 2). Instead of generic effects, write: "
            f"'{device_name} reveals how the community...' or '{device_name} demonstrates that...'"
        )
    
    # Device-specific guidance - THIS IS THE KEY FIX
    if detected_device and device_function:
        next_steps.append(
            f"Show how {detected_device.title()} functions: {device_function}"
        )
    
    sm2_next = ". ".join(next_steps) + "." if next_steps else "Build more distinct insights."
    
    return {'sm2': sm2, 'sm2_next': sm2_next}


def _generate_sm3_feedback(components: TVODEComponents, text: str) -> Dict[str, str]:
    """Generate SM3 (Cohesion Performance) feedback"""
    
    from .scoring import detect_grammar_errors
    
    variety = len(components.connector_types)
    total = sum(len(c) for c in components.connector_types.values())
    errors = detect_grammar_errors(text)
    
    # What's present
    if variety > 0:
        summary = []
        for ctype, conns in list(components.connector_types.items())[:4]:
            examples = ', '.join(conns[:3])
            summary.append(f"{ctype} ({examples})")
        sm3 = f"You use {total} connectors across {variety} types: {'; '.join(summary)}. "
    else:
        sm3 = f"You use {total} connectors across {variety} types. "
    
    sm3 += f"Approximately {errors} grammar issues detected."
    
    # Next steps
    next_steps = []
    
    if variety <= 1:
        missing = []
        if 'contrast' not in components.connector_types:
            missing.append("contrast (however, although, whereas)")
        if 'cause_effect' not in components.connector_types:
            missing.append("cause-effect (therefore, thus, consequently)")
        if 'elaboration' not in components.connector_types:
            missing.append("elaboration (which, whereby)")
        
        if missing:
            next_steps.append(f"Add connector variety: {', '.join(missing[:2])}")
    
    if errors > 2:
        next_steps.append("Focus on reducing grammar issues, especially subject-verb agreement")
    elif errors > 0:
        next_steps.append("Minor grammar cleanup needed (check subject-verb agreement, apostrophes)")
    
    sm3_next = ". ".join(next_steps) + "." if next_steps else "Good connector variety! Focus on grammar cleanup."
    
    return {'sm3': sm3, 'sm3_next': sm3_next}
