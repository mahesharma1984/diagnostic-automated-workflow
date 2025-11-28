"""
TVODE Evaluator Package v3.0

Evaluates student literary analysis using TVODE framework:
- Topic, Verb, Object, Detail, Effect components
- SM1 (Component Presence), SM2 (Density), SM3 (Cohesion) scoring
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
