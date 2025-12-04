# TVODE Evaluator v3.0 - Refactored

**Before:** 1 file, 1566 lines, impossible to debug  
**After:** 6 files, ~40KB total, each module testable independently

## Structure

```
tvode_evaluator/
├── __init__.py          # Package exports
├── taxonomies.py        # Static data (verbs, effects, connectors)
├── components.py        # Extract TVODE from text
├── device_context.py    # Kernel loading + device matching
├── scoring.py           # SM1, SM2, SM3 calculations
├── feedback.py          # Generate feedback strings
└── evaluator.py         # Main class (ties it together)
```

## What Each Module Does

| Module | Purpose | Test by |
|--------|---------|---------|
| `taxonomies.py` | Verb tiers, effect tiers, connectors | Import and check `VERB_TIERS` |
| `components.py` | Extract T, V, O, D, E from text | `extract_components("text")` |
| `device_context.py` | Load kernel, match devices | `ctx.load_kernel(); ctx.get_function("third-person limited")` |
| `scoring.py` | Calculate SM1, SM2, SM3 | `score_sm1(components)` |
| `feedback.py` | Generate feedback strings | `generate_feedback(...)` |
| `evaluator.py` | Orchestrate pipeline | `TVODEEvaluator().evaluate(...)` |

## Installation

Replace your old `tvode_evaluator.py` with this folder:

```bash
# Remove old file
rm tvode_evaluator.py

# Copy new module folder
cp -r tvode_evaluator/ your_project/
```

## Usage (unchanged)

```python
from tvode_evaluator import TVODEEvaluator

evaluator = TVODEEvaluator()
evaluator.load_kernel_context('kernels/The_Giver_kernel_v3_4.json')

result = evaluator.evaluate({
    'transcription': student_text
})

print(result.sm1_score)
print(result.feedback['sm2_next'])
```

## Key Fix: Device Function

The bug where feedback showed "functions: Me" instead of the actual description is fixed in `device_context.py` line 45:

```python
# OLD (broken):
'function': device.get('function', '')  # Gets "Me"

# NEW (fixed):
'function': device.get('pedagogical_function', device.get('function', ''))
```

## Testing Individual Modules

```python
# Test device loading
from tvode_evaluator.device_context import DeviceContext
ctx = DeviceContext()
ctx.load_kernel('kernels/The_Giver_kernel_v3_4.json')
print(ctx.get_function('third-person limited'))
# → "Creates intimacy with Jonas while maintaining narrative distance"

# Test component extraction
from tvode_evaluator.components import extract_components
components = extract_components("Lowry uses third person to reveal...")
print(components.topics)  # ['third person', 'Lowry']
print(components.verb_tiers)  # {'tier_1': ['reveal'], ...}

# Test scoring
from tvode_evaluator.scoring import score_sm1
sm1, ceiling = score_sm1(components)
print(f"SM1: {sm1}, Ceiling: {ceiling}")
```

## Debugging

If feedback is wrong:
1. Check `device_context.py` → Is kernel loading `pedagogical_function`?
2. Check `feedback.py` → Is `device_function` being used in SM2?

If scores are wrong:
1. Check `scoring.py` → Are tier weights correct?
2. Check `components.py` → Are verbs/effects being classified?

If device not matching:
1. Check `device_context.py` → `identify_device()` method
2. Check `taxonomies.py` → `DEVICE_ALIASES` dict

## Version History

- **v3.0** - Complete refactor into modules, fixed "Me" bug
- **v2.1** - Attempted patch (didn't work reliably)
- **v2.0** - Added Option A taxonomies
