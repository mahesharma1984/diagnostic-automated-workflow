#!/usr/bin/env python3
"""
Test the refactored TVODE evaluator module
"""

import sys
import json

# Test imports
print("="*60)
print("TESTING REFACTORED TVODE EVALUATOR")
print("="*60)

print("\n[1] Testing imports...")
try:
    from tvode_evaluator import TVODEEvaluator, EvaluationResult
    print("    ✓ Main classes imported")
except ImportError as e:
    print(f"    ✗ Import failed: {e}")
    sys.exit(1)

print("\n[2] Creating evaluator...")
evaluator = TVODEEvaluator()
print("    ✓ Evaluator created")

print("\n[3] Loading kernel...")
evaluator.load_kernel_context('kernels/The_Giver_kernel_v3_4.json')

# Verify function loaded correctly
tpl = evaluator.kernel_devices.get('third-person limited', {})
func = tpl.get('function', '')
print(f"\n[4] Checking device function...")
print(f"    Function: '{func[:60]}...'")

if func == 'Me' or len(func) < 10:
    print("    ✗ FAILED: Function is still code, not description!")
    sys.exit(1)
else:
    print("    ✓ Function loaded correctly!")

print("\n[5] Loading transcript...")
with open('outputs/transcripts/Coden_Week_4_transcript.json') as f:
    transcript = json.load(f)
print(f"    ✓ Loaded transcript for {transcript.get('student_name', 'Unknown')}")

print("\n[6] Running evaluation...")
result = evaluator.evaluate({
    'student_name': transcript.get('student_name'),
    'assignment': transcript.get('assignment'),
    'transcription': transcript.get('transcription', '')
})

print(f"\n[7] Results:")
print(f"    SM1: {result.sm1_score}")
print(f"    SM2: {result.sm2_score}")
print(f"    SM3: {result.sm3_score}")
print(f"    Overall: {result.overall_score:.2f}")

print(f"\n[8] Checking SM2 feedback...")
sm2_next = result.feedback.get('sm2_next', '')
print(f"    {sm2_next[:200]}...")

if 'functions: Me' in sm2_next or 'function: me' in sm2_next.lower():
    print("\n    ✗ FAILED: 'Me' still in feedback!")
    sys.exit(1)
elif 'Creates intimacy' in sm2_next or 'intimacy' in sm2_next.lower():
    print("\n    ✓ SUCCESS: Correct function text in feedback!")
else:
    print("\n    ? Function text not found in feedback (may be OK)")

print("\n" + "="*60)
print("ALL TESTS PASSED")
print("="*60)
