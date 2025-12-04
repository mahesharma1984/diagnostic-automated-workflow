#!/usr/bin/env python3
"""
Test the thesis evaluator module
"""

import sys
import json

# Test imports
print("="*60)
print("TESTING THESIS EVALUATOR")
print("="*60)

print("\n[1] Testing imports...")
try:
    from src.evaluators.thesis import ThesisEvaluator, ThesisEvaluationResult
    print("    ✓ Main classes imported")
except ImportError as e:
    print(f"    ✗ Import failed: {e}")
    sys.exit(1)

print("\n[2] Creating evaluator...")
evaluator = ThesisEvaluator()
print("    ✓ Evaluator created")

print("\n[3] Testing basic evaluation...")
test_text = """
I believe Jonas is more of a victim than a hero because 
he was forced to receive painful memories alone. This caused 
him to suffer isolation that nobody could understand.
"""

result = evaluator.evaluate({'transcription': test_text})

print(f"\n[4] Results:")
print(f"    SM1: {result.sm1_score}")
print(f"    SM2: {result.sm2_score}")
print(f"    SM3: {result.sm3_score}")
print(f"    Overall: {result.overall_score:.2f}")
print(f"    DCCEPS Layer: {result.dcceps_layer} ({result.dcceps_label})")

print(f"\n[5] Checking components...")
print(f"    Position: {result.components.position} ({result.components.position_strength})")
print(f"    Evidence quality: {result.components.evidence_quality}")
print(f"    Evidence items: {len(result.components.evidence_items)}")

print(f"\n[6] Checking feedback...")
print(f"    SM1 feedback: {result.feedback.get('sm1', 'N/A')[:100]}...")
print(f"    DCCEPS guidance: {result.feedback.get('dcceps_guidance', 'N/A')[:100]}...")

# Verify expected results
assert result.dcceps_layer >= 2, f"Expected DCCEPS layer >= 2, got {result.dcceps_layer}"
assert result.components.position in ["victim", "hero", "both_acknowledged"], f"Unexpected position: {result.components.position}"
assert result.overall_score > 0, "Overall score should be > 0"

print("\n" + "="*60)
print("ALL TESTS PASSED")
print("="*60)






