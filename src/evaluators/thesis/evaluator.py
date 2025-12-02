"""
Thesis Evaluator - Main evaluation class for argument/thesis quality

This is the primary interface for thesis assessment. It coordinates:
- Thesis component extraction (Position, Evidence, Reasoning, Counter-argument, Synthesis)
- DCCEPS layer assessment
- Scoring
- Feedback generation

Parallel to TVODEEvaluator but focused on argumentative structure rather than
analytical sentence structure.
"""

from dataclasses import dataclass, field
from typing import Dict, Union, Optional

from .thesis_components import ThesisComponents, extract_thesis_components
from .thesis_scoring import (
    score_thesis_sm1, score_thesis_sm2, score_thesis_sm3,
    calculate_overall_thesis_score
)
from .thesis_feedback import generate_thesis_feedback


@dataclass
class ThesisEvaluationResult:
    """Complete thesis evaluation output"""
    
    # Scores (parallel to TVODE)
    sm1_score: float  # Position + Evidence
    sm2_score: float  # Reasoning Depth
    sm3_score: float  # Argument Coherence
    overall_score: float
    total_points: float
    ceiling: float
    
    # DCCEPS specific
    dcceps_layer: int
    dcceps_label: str
    
    # Components and feedback
    components: ThesisComponents
    feedback: Dict[str, str]
    
    # API-specific fields (optional, populated when use_api=True)
    position: Optional[str] = None  # API-determined position
    position_strength: Optional[str] = None  # API-determined strength
    position_reasoning: Optional[str] = None  # API explanation
    dcceps_reasoning: Optional[str] = None  # API explanation
    evidence_quality: Optional[str] = None  # API-determined quality
    has_counter_argument: Optional[bool] = None  # API assessment
    has_synthesis: Optional[bool] = None  # API assessment


class ThesisEvaluator:
    """
    Main evaluator class for thesis/argument quality
    
    Usage:
        evaluator = ThesisEvaluator()
        result = evaluator.evaluate("I believe Jonas is more of a victim...")
        print(result.dcceps_layer)  # 1-4
        print(result.feedback['dcceps_guidance'])
    """
    
    def __init__(self):
        self.prompt_context = ""  # Store the writing prompt if provided
    
    def set_prompt_context(self, prompt: str) -> None:
        """
        Set the writing prompt for context-aware evaluation
        
        Args:
            prompt: The assignment prompt given to students
        """
        self.prompt_context = prompt
    
    def evaluate(
        self, 
        text: Union[str, Dict],
        kernel_path: str = None,
        reasoning_path: str = None,
        use_api: bool = True,
        api_key: Optional[str] = None,
        year_level: int = 8
    ) -> ThesisEvaluationResult:
        """
        Main evaluation pipeline
        
        Args:
            text: Student's argumentative writing (string) or dict with 'transcription' key
            kernel_path: Optional (not used for thesis evaluation)
            reasoning_path: Optional (not used for thesis evaluation)
            use_api: If True, use Claude API for scoring (recommended, default: True)
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            year_level: Student year level (7-12, default: 8)
        
        Returns:
            ThesisEvaluationResult with scores, DCCEPS layer, components, feedback
        """
        
        # Handle both string and dict inputs for compatibility
        if isinstance(text, dict):
            year_level = text.get('year_level', year_level)  # Extract from dict if present
            text = text.get('transcription', '')
        
        # Always extract components (rule-based) - provides context for API
        components = extract_thesis_components(text)
        
        if use_api:
            try:
                from .thesis_api_evaluator import evaluate_thesis_with_api
                api_result = evaluate_thesis_with_api(text, components, api_key, year_level=year_level)
                
                # Use API results for scores and assessments
                return ThesisEvaluationResult(
                    sm1_score=api_result['sm1_score'],
                    sm2_score=api_result['sm2_score'],
                    sm3_score=api_result['sm3_score'],
                    overall_score=api_result['overall_score'],
                    total_points=api_result['total_points'],
                    ceiling=api_result['ceiling'],
                    dcceps_layer=api_result['dcceps_layer'],
                    dcceps_label=api_result['dcceps_label'],
                    components=components,
                    feedback=api_result['feedback'],
                    # API-specific fields
                    position=api_result.get('position'),
                    position_strength=api_result.get('position_strength'),
                    position_reasoning=api_result.get('position_reasoning'),
                    dcceps_reasoning=api_result.get('dcceps_reasoning'),
                    evidence_quality=api_result.get('evidence_quality'),
                    has_counter_argument=api_result.get('has_counter_argument'),
                    has_synthesis=api_result.get('has_synthesis')
                )
            except ImportError as e:
                print(f"  ⚠ API unavailable ({e}), falling back to rule-based")
            except Exception as e:
                print(f"  ⚠ API error ({e}), falling back to rule-based")
        
        # Fallback: rule-based scoring (existing code)
        print(f"  ✓ Position: {components.position} ({components.position_strength})")
        print(f"  ✓ Evidence quality: {components.evidence_quality}")
        print(f"  ✓ DCCEPS Layer: {components.dcceps_layer} ({components.dcceps_label})")
        
        sm1_score, ceiling = score_thesis_sm1(components, text)
        sm2_score = score_thesis_sm2(components, text, ceiling)
        sm3_score = score_thesis_sm3(components, text, ceiling)
        
        overall, total_points = calculate_overall_thesis_score(sm1_score, sm2_score, sm3_score)
        
        feedback = generate_thesis_feedback(components, sm1_score, sm2_score, sm3_score, text)
        
        # Add metadata
        feedback['original_text'] = text
        if self.prompt_context:
            feedback['prompt_context'] = self.prompt_context
        
        return ThesisEvaluationResult(
            sm1_score=sm1_score,
            sm2_score=sm2_score,
            sm3_score=sm3_score,
            overall_score=overall,
            total_points=total_points,
            ceiling=ceiling,
            dcceps_layer=components.dcceps_layer,
            dcceps_label=components.dcceps_label,
            components=components,
            feedback=feedback
        )
    
    def evaluate_batch(self, texts: Dict[str, str]) -> Dict[str, ThesisEvaluationResult]:
        """
        Evaluate multiple students
        
        Args:
            texts: Dict of {student_name: text}
        
        Returns:
            Dict of {student_name: ThesisEvaluationResult}
        """
        
        results = {}
        for name, text in texts.items():
            print(f"\n{'='*60}")
            print(f"Evaluating: {name}")
            print('='*60)
            # Handle both string and dict inputs
            if isinstance(text, dict):
                text = text.get('transcription', '')
            results[name] = self.evaluate(text)
        
        return results
    
    def generate_report(self, result: ThesisEvaluationResult, student_name: str = "Student") -> str:
        """
        Generate a formatted report for a single evaluation
        
        Args:
            result: ThesisEvaluationResult from evaluate()
            student_name: Name to use in report
        
        Returns:
            Formatted markdown report string
        """
        
        report = f"""
# Thesis Quality Report: {student_name}

**Overall Score:** {result.overall_score:.1f}/5 ({result.total_points:.1f}/25 points)
**DCCEPS Layer Reached:** {result.dcceps_layer} ({result.dcceps_label})

---

## SM1: Position + Evidence ({result.sm1_score:.1f}/5)

{result.feedback['sm1']}

**Next Step:** {result.feedback['sm1_next']}

---

## SM2: Reasoning Depth ({result.sm2_score:.1f}/5)

{result.feedback['sm2']}

**Next Step:** {result.feedback['sm2_next']}

---

## SM3: Argument Coherence ({result.sm3_score:.1f}/5)

{result.feedback['sm3']}

**Next Step:** {result.feedback['sm3_next']}

---

## DCCEPS Progress

{result.feedback['dcceps_guidance']}

---

*Score Formula: (SM1 × 0.40) + (SM2 × 0.30) + (SM3 × 0.30) × 5 = Total Points*
"""
        
        return report


def format_comparative_summary(results: Dict[str, ThesisEvaluationResult]) -> str:
    """
    Generate comparative summary across multiple students
    
    Args:
        results: Dict of {student_name: ThesisEvaluationResult}
    
    Returns:
        Formatted markdown summary
    """
    
    summary = "# Thesis Quality: Comparative Summary\n\n"
    summary += "| Student | Overall | DCCEPS Layer | Position | Evidence | Key Strength | Key Growth Area |\n"
    summary += "|---------|---------|--------------|----------|----------|--------------|----------------|\n"
    
    for name, result in results.items():
        comp = result.components
        
        # Identify key strength
        if result.sm1_score >= 4.0:
            strength = "Clear position + specific evidence"
        elif result.sm2_score >= 4.0:
            strength = "Strong reasoning chains"
        elif result.sm3_score >= 4.0:
            strength = "Good argument coherence"
        elif comp.counter_arguments:
            strength = "Acknowledges counter-arguments"
        else:
            strength = "Attempts analysis"
        
        # Identify growth area
        if comp.position == "unclear":
            growth = "State clear position"
        elif comp.evidence_quality in ["assertion", "missing"]:
            growth = "Add specific evidence"
        elif result.dcceps_layer <= 1:
            growth = "Add comparative reasoning"
        elif result.dcceps_layer == 2:
            growth = "Add cause-effect logic"
        elif not comp.counter_arguments:
            growth = "Acknowledge other side"
        else:
            growth = "Strengthen synthesis"
        
        summary += f"| {name} | {result.overall_score:.1f}/5 | L{result.dcceps_layer} ({result.dcceps_label}) | {comp.position} | {comp.evidence_quality} | {strength} | {growth} |\n"
    
    # Class-wide patterns
    summary += "\n## Class-Wide Patterns\n\n"
    
    # Count DCCEPS layers
    layer_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for result in results.values():
        layer_counts[result.dcceps_layer] += 1
    
    summary += f"- **Layer 1 (Definition):** {layer_counts[1]} students\n"
    summary += f"- **Layer 2 (Comparison):** {layer_counts[2]} students\n"
    summary += f"- **Layer 3 (Cause-Effect):** {layer_counts[3]} students\n"
    summary += f"- **Layer 4 (Problem-Solution):** {layer_counts[4]} students\n"
    
    return summary
