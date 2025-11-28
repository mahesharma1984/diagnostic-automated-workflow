#!/usr/bin/env python3
"""
Automate CLI - Full pipeline (transcribe + evaluate)

Convenience wrapper that runs both stages in sequence.

Usage:
    python automate.py --image student.jpg --student "Name" --assignment "Week 4" --evaluator tvode
"""

import argparse
import json
import sys
from pathlib import Path

from src.transcriber import TVODETranscriber
from src.evaluators import get_evaluator, list_evaluators


def main():
    parser = argparse.ArgumentParser(
        description='Full diagnostic pipeline: transcribe + evaluate',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available evaluators: {', '.join(list_evaluators())}

Examples:
    # Basic usage
    python automate.py --image work.jpg --student "Coden" --assignment "Week 4" --evaluator tvode
    
    # With kernel
    python automate.py --image work.jpg --student "Coden" --assignment "Week 4" --evaluator tvode --kernel kernels/The_Giver.json
    
    # Skip review (auto-accept transcription)
    python automate.py --image work.jpg --student "Coden" --assignment "Week 4" --evaluator tvode --skip-review
        """
    )
    
    parser.add_argument(
        '--image', 
        nargs='+', 
        required=True,
        help='Path(s) to student work image(s)'
    )
    parser.add_argument(
        '--student', 
        required=True,
        help='Student name'
    )
    parser.add_argument(
        '--assignment', 
        required=True,
        help='Assignment name'
    )
    parser.add_argument(
        '--evaluator', 
        required=True,
        choices=list_evaluators(),
        help=f'Evaluator to use'
    )
    parser.add_argument(
        '--kernel',
        help='Path to kernel JSON file (optional)'
    )
    parser.add_argument(
        '--reasoning',
        help='Path to reasoning markdown file (optional)'
    )
    parser.add_argument(
        '--skip-review',
        action='store_true',
        help='Auto-accept transcription without review'
    )
    parser.add_argument(
        '--output', 
        default='./outputs',
        help='Output directory base (default: ./outputs)'
    )
    
    args = parser.parse_args()
    
    output_base = Path(args.output)
    
    # ========== STAGE 1: TRANSCRIBE ==========
    print(f"\n{'='*70}")
    print(f"STAGE 1: TRANSCRIBING")
    print(f"{'='*70}")
    
    try:
        transcriber = TVODETranscriber()
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    image_path = args.image if len(args.image) > 1 else args.image[0]
    
    transcript_result = transcriber.transcribe(
        image_path=image_path,
        student_name=args.student,
        assignment=args.assignment
    )
    
    # Save transcript
    transcript_dir = output_base / "transcripts"
    transcript_path = transcriber.save_result(transcript_result, transcript_dir)
    
    # ========== STAGE 2: REVIEW (if needed) ==========
    if transcript_result.requires_review and not args.skip_review:
        print(f"\n{'='*70}")
        print(f"STAGE 2: REVIEW NEEDED")
        print(f"{'='*70}")
        print(transcriber.format_review_prompt(transcript_result))
        print("\nEdit the transcript file manually, then re-run with:")
        print(f"  python evaluate.py --transcript {transcript_path} --evaluator {args.evaluator}")
        sys.exit(0)
    else:
        print(f"\n✓ Auto-accepting transcription")
    
    # ========== STAGE 3: EVALUATE ==========
    print(f"\n{'='*70}")
    print(f"STAGE 3: EVALUATING with {args.evaluator.upper()}")
    print(f"{'='*70}")
    
    EvaluatorClass = get_evaluator(args.evaluator)
    evaluator = EvaluatorClass()
    
    if args.kernel:
        evaluator.load_kernel_context(args.kernel)
    
    if args.reasoning:
        evaluator.load_reasoning_context(args.reasoning)
    
    result = evaluator.evaluate(
        {'transcription': transcript_result.transcription},
        kernel_path=args.kernel,
        reasoning_path=args.reasoning
    )
    
    print(f"\n✓ Evaluation complete")
    print(f"  SM1: {result.sm1_score}/5 (ceiling {result.ceiling})")
    print(f"  SM2: {result.sm2_score}/5")
    print(f"  SM3: {result.sm3_score}/5")
    print(f"  Overall: {result.overall_score:.1f}/5")
    
    # ========== STAGE 4: SAVE OUTPUTS ==========
    print(f"\n{'='*70}")
    print(f"STAGE 4: SAVING OUTPUTS")
    print(f"{'='*70}")
    
    safe_name = args.student.replace(' ', '_')
    safe_assignment = args.assignment.replace(' ', '_')
    
    # Save evaluation
    eval_dir = output_base / "evaluations"
    eval_dir.mkdir(parents=True, exist_ok=True)
    eval_path = eval_dir / f"{safe_name}_{safe_assignment}_{args.evaluator}_evaluation.json"
    
    eval_data = {
        'student': args.student,
        'assignment': args.assignment,
        'evaluator': args.evaluator,
        'scores': {
            'sm1': result.sm1_score,
            'sm2': result.sm2_score,
            'sm3': result.sm3_score,
            'overall': result.overall_score,
            'ceiling': result.ceiling
        },
        'feedback': result.feedback
    }
    
    with open(eval_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    # Save report
    report_dir = output_base / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{safe_name}_{safe_assignment}_{args.evaluator}_report.md"
    
    percentage = (result.overall_score / 5 * 100)
    report = f"""# {args.evaluator.upper()} Report Card

**Student:** {args.student}  
**Assignment:** {args.assignment}  
**Overall Score:** {result.overall_score:.1f}/5 ({percentage:.0f}%)

---

## SM1: {result.sm1_score}/5
{result.feedback.get('sm1', '')}

## SM2: {result.sm2_score}/5
{result.feedback.get('sm2', '')}

## SM3: {result.sm3_score}/5
{result.feedback.get('sm3', '')}
"""
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Summary
    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")
    print(f"Transcript: {transcript_path}")
    print(f"Evaluation: {eval_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
