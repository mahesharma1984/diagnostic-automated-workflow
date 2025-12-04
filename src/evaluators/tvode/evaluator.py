"""
TVODE Evaluator - Main evaluation class

This is the primary interface. It coordinates:
- Component extraction
- Device matching
- Scoring
- Feedback generation
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List

from .components import TVODEComponents, extract_components
from .device_context import DeviceContext
from .scoring import score_sm1, score_sm2, score_sm3
from .feedback import generate_feedback


@dataclass
class EvaluationResult:
    """Complete evaluation output"""
    sm1_score: float
    sm2_score: float
    sm3_score: float
    overall_score: float
    total_points: float
    components: TVODEComponents
    feedback: Dict[str, str]
    ceiling: float
    # New fields for SM2 depth dimensions
    distinct_insights: int = 0
    effect_dimensions: Dict[str, bool] = field(default_factory=lambda: {
        'reader_response': False,
        'meaning_creation': False,
        'thematic_impact': False
    })
    # New fields for SM3 grammar tracking
    grammar_error_count: int = 0
    grammar_errors: List[str] = field(default_factory=list)


class TVODEEvaluator:
    """Main evaluator class"""
    
    def __init__(self):
        self.device_ctx = DeviceContext()
    
    # Expose kernel_devices for backward compatibility
    @property
    def kernel_devices(self):
        return self.device_ctx.devices
    
    def load_kernel_context(self, kernel_path: str) -> None:
        """Load device definitions from kernel JSON"""
        self.device_ctx.load_kernel(kernel_path)
    
    def load_reasoning_context(self, reasoning_path: str) -> None:
        """Load reasoning excerpts from markdown"""
        self.device_ctx.load_reasoning(reasoning_path)
    
    def evaluate(
        self, 
        transcript_json: Dict, 
        kernel_path: str = None,
        reasoning_path: str = None,
        use_api: bool = True,  # API is now default
        api_key: str = None,
        use_rule_based: bool = False  # Fallback option
    ) -> EvaluationResult:
        """
        Main evaluation pipeline
        
        Uses Claude API for semantic evaluation by default. Falls back to rule-based
        if API fails or if use_rule_based=True.
        
        Args:
            transcript_json: Dict with 'transcription' key
            kernel_path: Optional path to kernel JSON
            reasoning_path: Optional path to reasoning markdown
            use_api: If True, use Claude API for scoring (default: True)
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            use_rule_based: If True, force rule-based evaluation (skip API)
        
        Returns:
            EvaluationResult with scores, components, feedback
        """
        
        # Load context if provided and not already loaded
        if kernel_path and not self.device_ctx.devices:
            self.device_ctx.load_kernel(kernel_path)
        if reasoning_path and not self.device_ctx.reasoning_context:
            self.device_ctx.load_reasoning(reasoning_path)
        
        text = transcript_json.get('transcription', '')
        
        # Step 1: Extract components (always rule-based - fast and works)
        components = extract_components(text)
        
        # Step 2: Identify device
        detected_device = self.device_ctx.identify_device(text, components.topics)
        
        if detected_device:
            name = self.device_ctx.devices[detected_device].get('name', detected_device)
            print(f"  ✓ Device identified: {name}")
        else:
            print(f"  ⚠ No device identified from topics: {components.topics[:5]}")
        
        # Try API first (unless rule-based is forced)
        if use_api and not use_rule_based:
            # API-based scoring (default)
            from .api_evaluator import evaluate_with_api
            
            try:
                api_result = evaluate_with_api(text, components, api_key)
                
                # Map API result to EvaluationResult
                feedback = api_result.get('feedback', {})
                feedback['original_text'] = text
                feedback['sm1'] = api_result.get('sm1_reasoning', '')
                feedback['sm2'] = api_result.get('sm2_reasoning', '')
                feedback['sm3'] = api_result.get('sm3_reasoning', '')
                feedback['sm1_next'] = feedback.get('sm1_next', '')
                feedback['sm2_next'] = feedback.get('sm2_next', '')
                feedback['sm3_next'] = feedback.get('sm3_next', '')
                feedback['one_line_fix'] = api_result.get('one_line_fix', '')
                
                if detected_device:
                    feedback['detected_device'] = detected_device
                    feedback['device_detection_type'] = 'explicit'
                
                # Extract API results for EvaluationResult fields
                distinct_insights = api_result.get('distinct_insights', 0)
                
                # Extract effect_dimensions from API response
                effect_dimensions = api_result.get('effect_dimensions', {
                    'reader_response': False,
                    'meaning_creation': False,
                    'thematic_impact': False
                })
                
                # Extract grammar errors (API returns grammar_errors)
                grammar_errors = api_result.get('grammar_errors', [])
                grammar_error_count = api_result.get('grammar_error_count', len(grammar_errors))
                
                # Add metadata to feedback
                feedback['distinct_insights'] = distinct_insights
                feedback['effect_dimensions'] = effect_dimensions
                feedback['grammar_error_count'] = grammar_error_count
                feedback['grammar_errors'] = grammar_errors
                feedback['grammar_issues'] = grammar_errors  # Backward compat
                
                return EvaluationResult(
                    sm1_score=api_result.get('sm1_score', 3.0),
                    sm2_score=api_result.get('sm2_score', 2.5),
                    sm3_score=api_result.get('sm3_score', 2.5),
                    overall_score=api_result.get('overall_score', 3.0),
                    total_points=api_result.get('total_points', 15.0),
                    components=components,
                    feedback=feedback,
                    ceiling=api_result.get('ceiling', 3.0),
                    distinct_insights=distinct_insights,
                    effect_dimensions=effect_dimensions,
                    grammar_error_count=grammar_error_count,
                    grammar_errors=grammar_errors or []
                )
            except Exception as e:
                print(f"  ⚠ API evaluation failed: {e}")
                print(f"  → Falling back to rule-based evaluation")
                use_rule_based = True  # Fall through to rule-based
        
        # Rule-based fallback (or if explicitly requested)
        if use_rule_based or not use_api:
            sm1_score, ceiling = score_sm1(components)
            sm2_score, effect_dimensions, distinct_insights = score_sm2(text, components, ceiling)
            sm3_score, grammar_error_count, grammar_errors = score_sm3(text, components, ceiling)
            
            # Step 4: Calculate overall
            overall = (sm1_score * 0.4) + (sm2_score * 0.3) + (sm3_score * 0.3)
            total_points = overall * 5
            
            # Step 5: Generate feedback
            feedback = generate_feedback(
                components, sm1_score, sm2_score, sm3_score,
                text, self.device_ctx, detected_device,
                effect_dimensions=effect_dimensions,
                distinct_insights=distinct_insights,
                grammar_error_count=grammar_error_count,
                grammar_errors=grammar_errors
            )
            
            # Add metadata
            feedback['original_text'] = text
            if detected_device:
                feedback['detected_device'] = detected_device
                feedback['device_detection_type'] = 'explicit'
            
            # Add new SM2 and SM3 metadata
            feedback['distinct_insights'] = distinct_insights
            feedback['effect_dimensions'] = effect_dimensions
            feedback['grammar_error_count'] = grammar_error_count
            feedback['grammar_errors'] = grammar_errors
            
            return EvaluationResult(
                sm1_score=sm1_score,
                sm2_score=sm2_score,
                sm3_score=sm3_score,
                overall_score=overall,
                total_points=total_points,
                components=components,
                feedback=feedback,
                ceiling=ceiling,
                distinct_insights=distinct_insights,
                effect_dimensions=effect_dimensions,
                grammar_error_count=grammar_error_count,
                grammar_errors=grammar_errors or []
            )
