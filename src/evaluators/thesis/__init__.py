"""
Thesis Evaluator Package v1.0

DCCEPS-based evaluation system for argumentative/thesis writing.

Parallel to TVODE Evaluator but assesses:
- Position clarity and strength
- Evidence quality and selection  
- Reasoning depth (DCCEPS layers)
- Counter-argument acknowledgment
- Synthesis quality

Usage:
    from src.evaluators.thesis import ThesisEvaluator, ThesisEvaluationResult
    
    evaluator = ThesisEvaluator()
    result = evaluator.evaluate({'transcription': "I believe Jonas is more of a victim..."}, use_api=True)
    
    print(result.dcceps_layer)  # 1-4
    print(result.dcceps_label)  # "Definition", "Comparison", "Cause-Effect", "Problem-Solution"
    print(result.feedback['dcceps_guidance'])

DCCEPS Layers:
    1 = Definition: Just identifies position
    2 = Comparison: Distinguishes between alternatives (more X than Y)
    3 = Cause-Effect: Shows HOW evidence supports position
    4 = Problem-Solution: Frames purpose/function of the argument
"""

from .evaluator import (
    ThesisEvaluator, 
    ThesisEvaluationResult,
    format_comparative_summary
)
from .thesis_components import ThesisComponents, extract_thesis_components
from .thesis_scoring import (
    score_thesis_sm1, 
    score_thesis_sm2, 
    score_thesis_sm3,
    calculate_overall_thesis_score
)
from .thesis_feedback import generate_thesis_feedback
from .thesis_api_evaluator import (
    evaluate_thesis_with_api,
    evaluate_thesis_batch,
    generate_thesis_report,
    THESIS_RUBRIC_PROMPT,
    THESIS_EVALUATION_PROMPT
)

__version__ = '1.0.0'

__all__ = [
    'ThesisEvaluator',
    'ThesisEvaluationResult',
    'ThesisComponents',
    'extract_thesis_components',
    'score_thesis_sm1',
    'score_thesis_sm2',
    'score_thesis_sm3',
    'calculate_overall_thesis_score',
    'generate_thesis_feedback',
    'format_comparative_summary',
    'evaluate_thesis_with_api',
    'evaluate_thesis_batch',
    'generate_thesis_report',
    'THESIS_RUBRIC_PROMPT',
    'THESIS_EVALUATION_PROMPT',
]
