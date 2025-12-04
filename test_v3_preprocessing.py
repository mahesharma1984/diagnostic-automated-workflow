#!/usr/bin/env python3
"""
Quick test to verify V3 transcription preprocessing is working.

Run from your project root:
    python test_v3_preprocessing.py

Expected output for Desmond:
    - Quality score: ~30%
    - Enhancement: aggressive
    - Issues: Low resolution, Overexposed, Very low contrast
"""

import sys
from pathlib import Path

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.transcriber import TVODETranscriber
    print("✓ Import successful: src.transcriber.TVODETranscriber")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("\nTrying direct import from src/transcriber/core.py...")
    try:
        from src.transcriber.core import TVODETranscriber
        print("✓ Direct import successful")
    except ImportError as e2:
        print(f"✗ Direct import also failed: {e2}")
        sys.exit(1)

# Check Pillow
try:
    from PIL import Image, ImageEnhance
    print("✓ Pillow installed")
except ImportError:
    print("✗ Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


def test_quality_assessment(transcriber, image_path: str, student: str):
    """Test quality assessment on an image."""
    print(f"\n{'─'*60}")
    print(f"Testing: {student}")
    print(f"Image: {image_path}")
    print(f"{'─'*60}")
    
    if not Path(image_path).exists():
        print(f"  ✗ File not found")
        return None
    
    # Test _assess_image_quality
    try:
        quality = transcriber._assess_image_quality(image_path)
        print(f"  Quality Score:  {quality['quality_score']:.0%}")
        print(f"  Resolution:     {quality['resolution']}")
        print(f"  Brightness:     {quality['brightness']:.1f}/255")
        print(f"  Contrast:       {quality['contrast']:.1f}")
        print(f"  Issues:         {', '.join(quality['issues']) if quality['issues'] else 'None'}")
        print(f"  Enhancement:    {quality['recommended_enhancement'].upper()}")
        print(f"  Usable:         {'✓ Yes' if quality['usable'] else '✗ No'}")
        return quality
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def test_preprocessing(transcriber, image_path: str, enhancement: str):
    """Test image preprocessing."""
    print(f"\n  Testing preprocessing with '{enhancement}' enhancement...")
    
    try:
        image_data, media_type = transcriber._preprocess_image(image_path, enhancement)
        size_kb = len(image_data) * 3 / 4 / 1024  # base64 to bytes to KB
        print(f"  ✓ Preprocessed: {size_kb:.1f} KB, {media_type}")
        return True
    except Exception as e:
        print(f"  ✗ Preprocessing failed: {e}")
        return False


def main():
    print("="*60)
    print("V3 TRANSCRIPTION PREPROCESSING TEST")
    print("="*60)
    
    # Initialize transcriber (API key not needed for preprocessing tests)
    # We'll mock it since we just want to test preprocessing
    import os
    
    # Temporarily set a fake key if not present (preprocessing doesn't use API)
    original_key = os.environ.get("ANTHROPIC_API_KEY")
    if not original_key:
        os.environ["ANTHROPIC_API_KEY"] = "test-key-for-preprocessing-only"
    
    try:
        transcriber = TVODETranscriber()
        print("✓ Transcriber initialized")
    except Exception as e:
        print(f"✗ Transcriber init failed: {e}")
        sys.exit(1)
    finally:
        # Restore original key
        if not original_key:
            del os.environ["ANTHROPIC_API_KEY"]
        
    # Test images - update these paths to match your setup
    test_images = {
        "Davin": "student_work/week_6/DavinLam_Week6.jpg",
        "Coden": "student_work/week_6/CodenChan_Week6.jpg",
        "Desmond": "student_work/week_6/DesmondLai_Week6.jpg",
    }
    
    # Also try alternate paths
    alt_paths = {
        "Davin": ["DavinLam_Week6.jpg", "uploads/DavinLam_Week6.jpg"],
        "Coden": ["CodenChan_Week6.jpg", "uploads/CodenChan_Week6.jpg"],
        "Desmond": ["DesmondLai_Week6.jpg", "uploads/DesmondLai_Week6.jpg"],
    }
    
    results = {}
    
    for student, image_path in test_images.items():
        # Try primary path first, then alternates
        paths_to_try = [image_path] + alt_paths.get(student, [])
        
        found_path = None
        for p in paths_to_try:
            if Path(p).exists():
                found_path = p
                break
        
        if not found_path:
            print(f"\n{'─'*60}")
            print(f"Testing: {student}")
            print(f"  ✗ No image found. Tried:")
            for p in paths_to_try:
                print(f"    - {p}")
            continue
        
        quality = test_quality_assessment(transcriber, found_path, student)
        
        if quality:
            results[student] = quality
            test_preprocessing(transcriber, found_path, quality['recommended_enhancement'])
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    if not results:
        print("\nNo images found to test. Update the paths in this script.")
        print("\nExpected structure:")
        print("  student_work/week_6/DavinLam_Week6.jpg")
        print("  student_work/week_6/CodenChan_Week6.jpg")
        print("  student_work/week_6/DesmondLai_Week6.jpg")
    else:
        print(f"\n{'Student':<12} {'Score':>8} {'Enhancement':>12} {'Issues'}")
        print("-"*60)
        for student, q in results.items():
            issues = ', '.join(q['issues'][:2]) if q['issues'] else 'None'
            if len(q['issues']) > 2:
                issues += f" (+{len(q['issues'])-2} more)"
            print(f"{student:<12} {q['quality_score']:>7.0%} {q['recommended_enhancement']:>12} {issues}")
    
    # Check for Desmond specifically
    if 'Desmond' in results:
        q = results['Desmond']
        print(f"\n{'─'*60}")
        print("DESMOND ANALYSIS (the problematic image):")
        print(f"{'─'*60}")
        
        if q['quality_score'] < 0.5:
            print("✓ Low quality correctly detected")
            print(f"  - Score: {q['quality_score']:.0%} (expected ~30%)")
        else:
            print(f"✗ Quality score higher than expected: {q['quality_score']:.0%}")
        
        if q['recommended_enhancement'] == 'aggressive':
            print("✓ Aggressive enhancement correctly recommended")
        else:
            print(f"✗ Expected 'aggressive', got '{q['recommended_enhancement']}'")
        
        if any('contrast' in i.lower() for i in q['issues']):
            print("✓ Low contrast issue detected")
        else:
            print("✗ Low contrast not detected")
        
        print("\nWith these settings, Desmond's image should now transcribe correctly.")
    
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
