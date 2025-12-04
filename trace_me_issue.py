#!/usr/bin/env python3
"""
DIAGNOSTIC: Trace where 'Me' is coming from in feedback generation
"""

import sys
import os
import shutil

print("="*70)
print("TRACING 'Me' IN FEEDBACK GENERATION")
print("="*70)

# Step 1: Clear ALL Python cache
print("\n[1] Clearing ALL Python cache...")
for root, dirs, files in os.walk('.'):
    for d in dirs:
        if d == '__pycache__':
            path = os.path.join(root, d)
            shutil.rmtree(path)
            print(f"    Deleted: {path}")

# Step 2: Clear imported modules
for mod in list(sys.modules.keys()):
    if 'tvode' in mod:
        del sys.modules[mod]

# Step 3: Fresh import
print("\n[2] Fresh import of evaluator...")
from tvode_evaluator import TVODEEvaluator
import json

# Step 4: Load transcript
print("\n[3] Loading transcript...")
with open('outputs/transcripts/Coden_Week_4_transcript.json') as f:
    transcript = json.load(f)

# Step 5: Create fresh evaluator and load kernel
print("\n[4] Creating fresh evaluator and loading kernel...")
evaluator = TVODEEvaluator()
evaluator.load_kernel_context('kernels/The_Giver_kernel_v3_4.json')

# Step 6: Check what's in kernel_devices
print("\n[5] Checking ALL kernel_devices functions...")
print("    Looking for any device with function='Me'...")
found_me = False
for device_name, device_data in evaluator.kernel_devices.items():
    func = device_data.get('function', '')
    if func == 'Me' or func == 'Te' or func == 'Re' or len(func) <= 3:
        print(f"    ✗ '{device_name}' has short/code function: {repr(func)}")
        found_me = True
    else:
        print(f"    ✓ '{device_name}': {func[:50]}...")

if not found_me:
    print("    ✓ No devices have code-only functions!")
else:
    print("    ✗ Some devices still have code functions - fix may not be complete")

# Step 7: Run evaluate with debugging
print("\n[6] Running evaluate()...")
transcript_json = {
    'student_name': transcript.get('student_name', 'Coden'),
    'assignment': transcript.get('assignment', 'Week 4'),
    'transcription': transcript.get('transcription', '')
}

result = evaluator.evaluate(transcript_json, kernel_path='kernels/The_Giver_kernel_v3_4.json')

# Step 8: Check feedback
print("\n[7] Checking generated feedback...")
sm2_next = result.feedback.get('sm2_next', '')
print(f"\nSM2 Next feedback:")
print(f"    {sm2_next[:400]}...")

# Check if 'Me' is in there
if 'functions: Me' in sm2_next or "function: me" in sm2_next.lower():
    print("\n    ✗ PROBLEM: 'Me' is still in the feedback!")
    
    # Check detected device
    student_device = result.feedback.get('detected_device')
    print(f"\n    Detected device: {student_device}")
    
    # Check what topics were extracted
    print(f"    Extracted topics: {result.components.topics[:5]}")
    
    # Trace which device would be selected as active_device
    print("\n    Tracing active_device selection...")
    for topic in result.components.topics:
        topic_lower = topic.lower().strip()
        if topic_lower in evaluator.kernel_devices:
            print(f"    → Topic '{topic}' MATCHES device '{topic_lower}'")
            print(f"       Function: {evaluator.kernel_devices[topic_lower].get('function', 'N/A')}")
            break
        else:
            # Check fuzzy match
            for dev_name in evaluator.kernel_devices.keys():
                if topic_lower in dev_name or dev_name in topic_lower:
                    print(f"    → Topic '{topic}' FUZZY MATCHES device '{dev_name}'")
                    print(f"       Function: {evaluator.kernel_devices[dev_name].get('function', 'N/A')}")
                    break
            else:
                print(f"    → Topic '{topic}' - no match")
                continue
            break
    
    # Also check device_context
    if student_device:
        device_context = evaluator._get_device_context(student_device)
        print(f"\n    device_context for '{student_device}':")
        if device_context and 'kernel' in device_context:
            kernel_data = device_context['kernel']
            print(f"       function: {repr(kernel_data.get('function', 'NOT SET'))}")
        else:
            print(f"       NO KERNEL DATA!")
else:
    print("\n    ✓ SUCCESS: 'Me' is NOT in the feedback!")

print("\n" + "="*70)
