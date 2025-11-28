"""
TVODE Evaluator - Main evaluation class

This is the primary interface. It coordinates:
- Component extraction
- Device matching
- Scoring
- Feedback generation
"""

from dataclasses import dataclass
from typing import Dict, Optional

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
        reasoning_path: str = None
    ) -> EvaluationResult:
        """
        Main evaluation pipeline
        
        Args:
            transcript_json: Dict with 'transcription' key
            kernel_path: Optional path to kernel JSON
            reasoning_path: Optional path to reasoning markdown
        
        Returns:
            EvaluationResult with scores, components, feedback
        """
        
        # Load context if provided and not already loaded
        if kernel_path and not self.device_ctx.devices:
            self.device_ctx.load_kernel(kernel_path)
        if reasoning_path and not self.device_ctx.reasoning_context:
            self.device_ctx.load_reasoning(reasoning_path)
        
        text = transcript_json.get('transcription', '')
        
        # Step 1: Extract components
        components = extract_components(text)
        
        # Step 2: Identify device
        detected_device = self.device_ctx.identify_device(text, components.topics)
        
        if detected_device:
            name = self.device_ctx.devices[detected_device].get('name', detected_device)
            print(f"  ✓ Device identified: {name}")
        else:
            print(f"  ⚠ No device identified from topics: {components.topics[:5]}")
        
        # Step 3: Score
        sm1_score, ceiling = score_sm1(components)
        sm2_score = score_sm2(text, components, ceiling)
        sm3_score = score_sm3(text, components, ceiling)
        
        # Step 4: Calculate overall
        overall = (sm1_score * 0.4) + (sm2_score * 0.3) + (sm3_score * 0.3)
        total_points = overall * 5
        
        # Step 5: Generate feedback
        feedback = generate_feedback(
            components, sm1_score, sm2_score, sm3_score,
            text, self.device_ctx, detected_device
        )
        
        # Add metadata
        feedback['original_text'] = text
        if detected_device:
            feedback['detected_device'] = detected_device
            feedback['device_detection_type'] = 'explicit'
        
        return EvaluationResult(
            sm1_score=sm1_score,
            sm2_score=sm2_score,
            sm3_score=sm3_score,
            overall_score=overall,
            total_points=total_points,
            components=components,
            feedback=feedback,
            ceiling=ceiling
        )
