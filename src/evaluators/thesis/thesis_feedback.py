"""
Thesis Feedback Generation

Generates contextualized feedback for thesis/argument quality.
Uses DCCEPS layers to guide improvement suggestions.
"""

from typing import Dict

from .thesis_components import ThesisComponents
from .thesis_taxonomies import DCCEPS_LAYERS


def generate_thesis_feedback(
    components: ThesisComponents,
    sm1: float, sm2: float, sm3: float,
    text: str
) -> Dict[str, str]:
    """
    Generate feedback for thesis quality
    
    Returns:
        Dict with sm1, sm1_next, sm2, sm2_next, sm3, sm3_next, dcceps_guidance
    """
    
    feedback = {}
    
    # Generate each section
    feedback.update(_generate_position_feedback(components))
    feedback.update(_generate_reasoning_feedback(components))
    feedback.update(_generate_coherence_feedback(components, text))
    feedback.update(_generate_dcceps_guidance(components))
    
    return feedback


def _generate_position_feedback(components: ThesisComponents) -> Dict[str, str]:
    """Generate SM1 (Position + Evidence) feedback"""
    
    # Current status
    if components.position == "unclear":
        sm1 = "Your position is not clear. The reader can't tell if you think Jonas is more hero or victim."
    else:
        sm1 = f"You take a clear position: Jonas is more of a {components.position}. "
        sm1 += f"Your stance is {components.position_strength}. "
        sm1 += f"Your evidence is {components.evidence_quality}."
    
    # Next steps
    next_steps = []
    
    # Position clarity
    if components.position_strength == "missing":
        next_steps.append(
            "State your position clearly early in your response: "
            "'I believe Jonas is more of a [hero/victim] because...'"
        )
    elif components.position_strength == "hedged":
        next_steps.append(
            "Strengthen your stance. Instead of 'maybe' or 'kind of,' use "
            "'I believe' or 'It is clear that...'"
        )
    
    # Evidence quality
    if components.evidence_quality in ["assertion", "missing"]:
        next_steps.append(
            "Add specific evidence. Name the exact scene or quote: "
            "'When Jonas receives the memory of warfare where a boy dies begging for water, this shows...'"
        )
    elif components.evidence_quality == "general":
        next_steps.append(
            "Make your evidence more specific. Instead of 'he tried to help,' say "
            "'When Jonas took Gabriel on the bicycle and escaped the community...'"
        )
    elif components.evidence_quality == "paraphrased":
        next_steps.append(
            "Consider adding a direct quote to strengthen your evidence: "
            "\"Jonas felt 'a surge of pride'\" with the specific page reference."
        )
    
    sm1_next = " ".join(next_steps) if next_steps else "Good position clarity and evidence!"
    
    return {'sm1': sm1, 'sm1_next': sm1_next}


def _generate_reasoning_feedback(components: ThesisComponents) -> Dict[str, str]:
    """Generate SM2 (Reasoning Depth) feedback"""
    
    # Current status
    sm2 = f"Your argument reaches DCCEPS Layer {components.dcceps_layer}: {components.dcceps_label}. "
    
    # Count reasoning types
    ce_count = len(components.reasoning_types.get('cause_effect', []))
    comp_count = len(components.reasoning_types.get('comparison', []))
    
    sm2 += f"You use {ce_count} cause-effect connections and {comp_count} comparisons."
    
    # Next steps based on current layer
    next_steps = []
    
    if components.dcceps_layer == 0:
        next_steps.append(
            "First, state a clear position: 'Jonas is more of a victim/hero because...' "
            "Then explain WHY your evidence supports this."
        )
    elif components.dcceps_layer == 1:
        next_steps.append(
            "Move from Definition to Comparison. You've stated Jonas is a [hero/victim]. "
            "Now show why he's MORE of one than the other: "
            "'While Jonas does [hero action], he suffers MORE from [victim experience], therefore...'"
        )
    elif components.dcceps_layer == 2:
        next_steps.append(
            "Move from Comparison to Cause-Effect. You've compared hero vs victim qualities. "
            "Now explain the CAUSE: 'Because Jonas was forced to receive memories alone, "
            "he experienced isolation which caused his suffering to outweigh his heroic acts.'"
        )
    elif components.dcceps_layer == 3:
        next_steps.append(
            "To reach Layer 4 (Problem-Solution), frame the PURPOSE: "
            "'The text presents Jonas as more victim than hero in order to critique "
            "how the community sacrifices individuals for collective stability.'"
        )
    else:
        next_steps.append(
            "Excellent reasoning depth! To refine further, ensure each cause-effect "
            "chain is supported by specific textual evidence."
        )
    
    sm2_next = " ".join(next_steps)
    
    return {'sm2': sm2, 'sm2_next': sm2_next}


def _generate_coherence_feedback(components: ThesisComponents, text: str) -> Dict[str, str]:
    """Generate SM3 (Argument Coherence) feedback"""
    
    # Current status
    sm3 = ""
    
    if components.counter_arguments:
        sm3 += "You acknowledge the other side, which strengthens your argument. "
    else:
        sm3 += "You don't acknowledge counter-arguments. "
    
    if components.synthesis:
        sm3 += "You have a concluding synthesis that ties your argument together."
    else:
        sm3 += "Your conclusion could be stronger."
    
    # Next steps
    next_steps = []
    
    if not components.counter_arguments:
        if components.position == "hero":
            next_steps.append(
                "Acknowledge the other side: 'Although Jonas does suffer as a victim "
                "(being forced to receive painful memories), his heroic actions outweigh this because...'"
            )
        else:
            next_steps.append(
                "Acknowledge the other side: 'While Jonas does show heroic qualities "
                "(escaping with Gabriel), his suffering as a victim is greater because...'"
            )
    
    if not components.synthesis:
        next_steps.append(
            "Add a strong conclusion that weighs the evidence: "
            "'Therefore, when we weigh Jonas's suffering against his heroic acts, "
            "it becomes clear that he is more of a [victim/hero] because...'"
        )
    elif components.synthesis_score < 0.75:
        next_steps.append(
            "Strengthen your conclusion by explicitly weighing the evidence: "
            "'Overall, the evidence shows that Jonas suffered more than he saved, "
            "making him more victim than hero.'"
        )
    
    sm3_next = " ".join(next_steps) if next_steps else "Good argument coherence!"
    
    return {'sm3': sm3, 'sm3_next': sm3_next}


def _generate_dcceps_guidance(components: ThesisComponents) -> Dict[str, str]:
    """Generate overall DCCEPS progression guidance"""
    
    layer = components.dcceps_layer
    
    if layer == 0:
        guidance = (
            "**Your argument needs a clear foundation.**\n\n"
            "Start with Layer 1 (Definition): State clearly whether Jonas is more hero or victim.\n"
            "Example: 'I believe Jonas is more of a victim than a hero.'"
        )
    elif layer == 1:
        guidance = (
            "**You're at Layer 1: Definition** - You state a position.\n\n"
            "To reach Layer 2 (Comparison): Show WHY hero qualities are less than victim qualities.\n"
            "Example: 'Jonas is more victim than hero because while he saved Gabriel, "
            "he suffered through hundreds of painful memories alone.'"
        )
    elif layer == 2:
        guidance = (
            "**You're at Layer 2: Comparison** - You distinguish between alternatives.\n\n"
            "To reach Layer 3 (Cause-Effect): Explain HOW the evidence creates meaning.\n"
            "Example: 'Because Jonas was the only person who could see the truth about release, "
            "he was isolated from everyone, which caused profound suffering that no heroic act could undo.'"
        )
    elif layer == 3:
        guidance = (
            "**You're at Layer 3: Cause-Effect** - You show how evidence supports your position.\n\n"
            "To reach Layer 4 (Problem-Solution): Frame the PURPOSE of this configuration.\n"
            "Example: 'The text positions Jonas as victim rather than hero in order to critique "
            "how the community's pursuit of sameness requires sacrificing individuals.'"
        )
    else:
        guidance = (
            "**You've reached Layer 4: Problem-Solution** - Excellent argument structure!\n\n"
            "To refine: Ensure every claim is supported by specific textual evidence, "
            "and that your counter-argument acknowledgment is fully integrated into your reasoning chain."
        )
    
    return {'dcceps_guidance': guidance, 'dcceps_layer_reached': str(layer)}





