"""
TVODE Evaluator Package v3.0

Modular evaluation system for literary analysis.

Usage:
    from tvode_evaluator import TVODEEvaluator, EvaluationResult
    
    evaluator = TVODEEvaluator()
    evaluator.load_kernel_context('kernels/The_Giver_kernel_v3_4.json')
    
    result = evaluator.evaluate({'transcription': student_text})
    print(result.sm1_score, result.feedback['sm1'])
"""

from .evaluator import TVODEEvaluator, EvaluationResult
from .components import TVODEComponents, extract_components
from .device_context import DeviceContext
from .scoring import score_sm1, score_sm2, score_sm3
from .feedback import generate_feedback

__version__ = '3.0.0'

__all__ = [
    'TVODEEvaluator',
    'EvaluationResult', 
    'TVODEComponents',
    'DeviceContext',
    'extract_components',
    'score_sm1',
    'score_sm2', 
    'score_sm3',
    'generate_feedback',
]
