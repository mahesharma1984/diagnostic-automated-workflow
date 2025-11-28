"""
Evaluators Registry

Maps evaluator names to their classes.
Add new evaluators here.
"""

from .tvode import TVODEEvaluator

# Registry: name -> evaluator class
EVALUATORS = {
    'tvode': TVODEEvaluator,
    # 'dcceps': DCCEPSEvaluator,  # Add when ready
}

def get_evaluator(name: str):
    """Get evaluator class by name"""
    if name not in EVALUATORS:
        available = ', '.join(EVALUATORS.keys())
        raise ValueError(f"Unknown evaluator: '{name}'. Available: {available}")
    return EVALUATORS[name]

def list_evaluators():
    """List available evaluator names"""
    return list(EVALUATORS.keys())

__all__ = ['EVALUATORS', 'get_evaluator', 'list_evaluators']
