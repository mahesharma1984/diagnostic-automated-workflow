# Developer Guide

Guide for extending and customizing the diagnostic workflow system.

## Architecture Overview

The system follows a modular, registry-based architecture:

```
┌─────────────┐
│  CLI Layer  │  transcribe.py, evaluate.py, automate.py
└──────┬──────┘
       │
┌──────▼──────────────────┐
│   Core Modules          │
│  ┌──────────────┐       │
│  │ Transcriber  │       │  src/transcriber/
│  └──────────────┘       │
│  ┌──────────────┐       │
│  │ Evaluators   │       │  src/evaluators/
│  │  Registry    │       │
│  └──────┬───────┘       │
│         │                │
│  ┌──────▼─────────────┐ │
│  │ TVODE Evaluator    │ │  src/evaluators/tvode/
│  │ (and future ones)  │ │
│  └────────────────────┘ │
└─────────────────────────┘
```

## Adding a New Evaluator

### Step 1: Create Evaluator Directory

```bash
mkdir -p src/evaluators/my_evaluator
touch src/evaluators/my_evaluator/__init__.py
touch src/evaluators/my_evaluator/evaluator.py
```

### Step 2: Implement Evaluator Class

```python
# src/evaluators/my_evaluator/evaluator.py
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class MyEvaluationResult:
    """Result structure for your evaluator"""
    overall_score: float
    component_scores: Dict[str, float]
    feedback: Dict[str, str]
    # Add your specific fields

class MyEvaluator:
    """Your evaluator implementation"""
    
    def __init__(self):
        # Initialize any required resources
        pass
    
    def evaluate(
        self, 
        data: Dict[str, Any],
        kernel_path: Optional[str] = None,
        reasoning_path: Optional[str] = None,
        **kwargs
    ) -> MyEvaluationResult:
        """
        Main evaluation method.
        
        Args:
            data: Dict containing 'transcription' key with text
            kernel_path: Optional path to kernel JSON
            reasoning_path: Optional path to reasoning document
            **kwargs: Additional evaluator-specific args
        
        Returns:
            MyEvaluationResult instance
        """
        transcription = data.get('transcription', '')
        
        # Your evaluation logic here
        scores = self._calculate_scores(transcription)
        feedback = self._generate_feedback(scores)
        
        return MyEvaluationResult(
            overall_score=scores['overall'],
            component_scores=scores,
            feedback=feedback
        )
    
    def load_kernel_context(self, kernel_path: str):
        """Load device context from kernel file"""
        # Implement if needed
        pass
    
    def load_reasoning_context(self, reasoning_path: str):
        """Load reasoning document"""
        # Implement if needed
        pass
    
    def _calculate_scores(self, text: str) -> Dict[str, float]:
        """Your scoring logic"""
        # Implement your rubric
        return {'overall': 0.0}
    
    def _generate_feedback(self, scores: Dict[str, float]) -> Dict[str, str]:
        """Generate feedback based on scores"""
        return {}
```

### Step 3: Export from Package

```python
# src/evaluators/my_evaluator/__init__.py
from .evaluator import MyEvaluator

__all__ = ['MyEvaluator']
```

### Step 4: Register in Registry

```python
# src/evaluators/__init__.py
from .tvode import TVODEEvaluator
from .my_evaluator import MyEvaluator  # Add import

EVALUATORS = {
    'tvode': TVODEEvaluator,
    'my_evaluator': MyEvaluator,  # Add to registry
}

# Rest of file unchanged...
```

### Step 5: Test

```bash
python evaluate.py \
  --transcript outputs/transcripts/test_transcript.json \
  --evaluator my_evaluator
```

## Extending the Transcriber

The transcriber is currently TVODE-specific but can be extended:

```python
# src/transcriber/core.py
class TVODETranscriber:
    # Current implementation
    pass

# Future: Add other transcribers
class GenericTranscriber:
    # More general implementation
    pass
```

To add a new transcriber, you could:

1. Add it to `src/transcriber/` as a new module
2. Update `src/transcriber/__init__.py` to export it
3. Modify `transcribe.py` to accept a `--transcriber` flag

## Customizing Output Formats

### Changing Report Format

Edit the report generation in `evaluate.py`:

```python
# Around line 170-203
report = f"""# Your Custom Format

## Section 1
{result.feedback.get('section1', '')}

## Section 2
{result.feedback.get('section2', '')}
"""
```

### Changing Evaluation JSON Structure

Modify the `eval_data` dictionary in `evaluate.py`:

```python
eval_data = {
    'student': student_name,
    'assignment': assignment,
    'evaluator': args.evaluator,
    'scores': {
        # Your custom score structure
    },
    'custom_field': 'value',
}
```

## Testing

### Unit Tests

Create test files:

```bash
mkdir -p tests
touch tests/test_evaluators.py
touch tests/test_transcriber.py
```

Example test:

```python
# tests/test_evaluators.py
import unittest
from src.evaluators import get_evaluator, list_evaluators

class TestEvaluatorRegistry(unittest.TestCase):
    def test_list_evaluators(self):
        evaluators = list_evaluators()
        self.assertIn('tvode', evaluators)
    
    def test_get_evaluator(self):
        EvaluatorClass = get_evaluator('tvode')
        evaluator = EvaluatorClass()
        self.assertIsNotNone(evaluator)
```

### Integration Tests

Test the full pipeline:

```bash
# Create test script
python -c "
from src.transcriber import TVODETranscriber
from src.evaluators import get_evaluator

# Test transcription
transcriber = TVODETranscriber()
# ... test code

# Test evaluation
EvaluatorClass = get_evaluator('tvode')
evaluator = EvaluatorClass()
# ... test code
"
```

## Code Style

- Follow PEP 8
- Use type hints
- Document public methods with docstrings
- Keep functions focused and small
- Use dataclasses for result structures

## Performance Considerations

### Caching

Consider caching expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(text: str):
    # Cache results for repeated inputs
    pass
```

### Batch Processing

For processing multiple students, consider:

1. Parallel processing with `multiprocessing`
2. Batch API calls where possible
3. Progress tracking for long operations

## Error Handling

### API Errors

Handle API failures gracefully:

```python
try:
    result = api_call()
except APIError as e:
    logger.error(f"API call failed: {e}")
    # Retry logic or fallback
    raise
```

### Validation

Validate inputs early:

```python
def evaluate(self, data: Dict[str, Any], **kwargs):
    if 'transcription' not in data:
        raise ValueError("Missing 'transcription' in data")
    
    transcription = data['transcription']
    if not transcription or not isinstance(transcription, str):
        raise ValueError("Invalid transcription format")
    
    # Continue with evaluation
```

## Logging

Add logging for debugging:

```python
import logging

logger = logging.getLogger(__name__)

def evaluate(self, data, **kwargs):
    logger.info(f"Starting evaluation with {len(data['transcription'])} chars")
    # ... evaluation logic
    logger.debug(f"Calculated scores: {scores}")
```

## Contributing

When adding features:

1. Create a feature branch
2. Add tests
3. Update documentation
4. Ensure all tests pass
5. Submit pull request

## Questions?

- Check existing evaluator implementations in `src/evaluators/tvode/`
- Review CLI scripts for usage patterns
- See `README.md` for user-facing documentation

