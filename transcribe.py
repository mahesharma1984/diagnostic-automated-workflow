#!/usr/bin/env python3
"""
Transcribe CLI - Stage 1 of diagnostic pipeline

Converts handwritten student work images to structured JSON transcripts.

Usage:
    python transcribe.py --image student.jpg --student "Name" --assignment "Week 4"
    python transcribe.py --image page1.jpg page2.jpg --student "Name" --assignment "Week 4"

Output:
    outputs/transcripts/{student}_{assignment}_transcript.json
"""

import argparse
import sys
from pathlib import Path

from src.transcriber import TVODETranscriber


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe handwritten student work to JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single page
    python transcribe.py --image work.jpg --student "Coden" --assignment "Week 4"
    
    # Multiple pages
    python transcribe.py --image page1.jpg page2.jpg --student "Coden" --assignment "Week 4"
    
    # Custom output directory
    python transcribe.py --image work.jpg --student "Coden" --assignment "Week 4" --output ./my_outputs
        """
    )
    
    parser.add_argument(
        '--image', 
        nargs='+', 
        required=True,
        help='Path(s) to student work image(s) - supports multiple pages'
    )
    parser.add_argument(
        '--student', 
        required=True,
        help='Student name'
    )
    parser.add_argument(
        '--assignment', 
        required=True,
        help='Assignment name (e.g., "Week 4")'
    )
    parser.add_argument(
        '--output', 
        default='./outputs/transcripts',
        help='Output directory (default: ./outputs/transcripts)'
    )
    
    args = parser.parse_args()
    
    # Validate image paths
    for img_path in args.image:
        if not Path(img_path).exists():
            print(f"ERROR: Image not found: {img_path}")
            sys.exit(1)
    
    # Initialize transcriber
    try:
        transcriber = TVODETranscriber()
    except ValueError as e:
        print(f"ERROR: {e}")
        print("Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    
    # Run transcription
    print(f"\n{'='*60}")
    print(f"TRANSCRIBING: {args.student} - {args.assignment}")
    print(f"{'='*60}")
    
    image_path = args.image if len(args.image) > 1 else args.image[0]
    
    result = transcriber.transcribe(
        image_path=image_path,
        student_name=args.student,
        assignment=args.assignment
    )
    
    # Save result
    output_dir = Path(args.output)
    output_path = transcriber.save_result(result, output_dir)
    
    # Summary
    print(f"\n{'='*60}")
    print("TRANSCRIPTION COMPLETE")
    print(f"{'='*60}")
    print(f"Output: {output_path}")
    print(f"Words: {result.word_count}")
    print(f"Accuracy: {result.accuracy_score:.1%}")
    print(f"Review needed: {'YES' if result.requires_review else 'NO'}")
    
    if result.requires_review:
        print(f"\nRun evaluate.py after reviewing/correcting the transcript.")
    else:
        print(f"\nReady for evaluation:")
        print(f"  python evaluate.py --transcript {output_path} --evaluator tvode")


if __name__ == "__main__":
    main()
