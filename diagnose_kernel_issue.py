#!/usr/bin/env python3
"""
DIAGNOSTIC: Find why kernel function isn't being used in feedback

Run this from your project root:
    python3 diagnose_kernel_issue.py
"""

import sys
import os

print("="*70)
print("TVODE KERNEL LOADING DIAGNOSTIC")
print("="*70)

# Step 1: Clear cached imports
print("\n[1] Clearing Python cache...")
for mod in list(sys.modules.keys()):
    if 'tvode' in mod:
        del sys.modules[mod]
        print(f"    Cleared: {mod}")

# Step 2: Check kernel file exists
kernel_path = 'kernels/The_Giver_kernel_v3_4.json'
print(f"\n[2] Checking kernel file: {kernel_path}")
if os.path.exists(kernel_path):
    print(f"    ✓ File exists")
else:
    print(f"    ✗ FILE NOT FOUND - check path!")
    sys.exit(1)

# Step 3: Load kernel and check raw data
print(f"\n[3] Loading kernel JSON directly...")
import json
with open(kernel_path) as f:
    kernel = json.load(f)

# Find third-person limited device
tpl_device = None
for device in kernel.get('micro_devices', []):
    if device.get('name', '').lower() == 'third-person limited':
        tpl_device = device
        break

if tpl_device:
    print(f"    Found 'Third-Person Limited' in kernel")
    print(f"    Raw 'function' field: {repr(tpl_device.get('function', 'N/A'))}")
    print(f"    Raw 'pedagogical_function' field: {repr(tpl_device.get('pedagogical_function', 'N/A')[:60])}...")
else:
    print(f"    ✗ 'Third-Person Limited' not found in kernel!")

# Step 4: Check what evaluator loads
print(f"\n[4] Testing TVODEEvaluator.load_kernel_context()...")
from tvode_evaluator import TVODEEvaluator

evaluator = TVODEEvaluator()
evaluator.load_kernel_context(kernel_path)

device_data = evaluator.kernel_devices.get('third-person limited', {})
loaded_function = device_data.get('function', 'NOT FOUND')

print(f"    Loaded function: {repr(loaded_function)}")

# Step 5: Diagnose the problem
print(f"\n[5] DIAGNOSIS:")
print("="*70)

if loaded_function == 'Me':
    print("    ✗ PROBLEM: Evaluator is loading 'function' field (code)")
    print("    ✗ The fix to use 'pedagogical_function' was NOT applied")
    print("")
    print("    ACTION: Check tvode_evaluator.py line ~316-322")
    print("    It should say:")
    print("        'function': device.get('pedagogical_function', device.get('function', '')),")
    print("    NOT:")
    print("        'function': device.get('function', ''),")
elif 'intimacy' in loaded_function.lower() or 'jonas' in loaded_function.lower():
    print("    ✓ Evaluator IS loading pedagogical_function correctly!")
    print(f"    ✓ Function: '{loaded_function[:60]}...'")
    print("")
    print("    PROBLEM must be elsewhere - kernel loads correctly but")
    print("    feedback generation isn't using it.")
    print("")
    print("    Check _generate_feedback() method around line 1340-1350")
else:
    print(f"    ? Unexpected function value: {loaded_function}")
    print("    Check kernel file for correct pedagogical_function")

# Step 6: Check the actual line in evaluator
print(f"\n[6] Checking tvode_evaluator.py source code...")
with open('tvode_evaluator.py', 'r') as f:
    content = f.read()

if "device.get('pedagogical_function'" in content:
    print("    ✓ 'pedagogical_function' IS in the code")
else:
    print("    ✗ 'pedagogical_function' NOT FOUND in code - fix not applied!")

if "if device_name_lower in self.kernel_devices:" in content:
    print("    ✓ Duplicate skip logic IS in the code")
else:
    print("    ✗ Duplicate skip logic NOT FOUND - fix not fully applied!")

print("\n" + "="*70)
print("END DIAGNOSTIC")
print("="*70)
