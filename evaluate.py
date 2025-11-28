#!/usr/bin/env python3
"""
Evaluate CLI - Stage 2 of diagnostic pipeline

Evaluates a JSON transcript against a rubric and generates a report.

Usage:
    python evaluate.py --transcript outputs/transcripts/Name_Week_4_transcript.json --evaluator tvode
    python evaluate.py --transcript transcript.json --evaluator tvode --kernel kernels/The_Giver.json

Output:
    outputs/evaluations/{student}_{assignment}_{evaluator}_evaluation.json
    outputs/reports/{student}_{assignment}_{evaluator}_report.md
"""

import argparse
import json
import sys
from pathlib import Path

from src.evaluators import get_evaluator, list_evaluators


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate a transcript against a rubric',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available evaluators: {', '.join(list_evaluators())}

Examples:
    # Basic evaluation
    python evaluate.py --transcript outputs/transcripts/Coden_Week_4_transcript.json --evaluator tvode
    
    # With kernel context
    python evaluate.py --transcript transcript.json --evaluator tvode --kernel kernels/The_Giver.json
    
    # Custom output directory
    python evaluate.py --transcript transcript.json --evaluator tvode --output ./my_outputs
        """
    )
    
    parser.add_argument(
        '--transcript', 
        required=True,
        help='Path to transcript JSON file'
    )
    parser.add_argument(
        '--evaluator', 
        required=True,
        choices=list_evaluators(),
        help=f'Evaluator to use: {", ".join(list_evaluators())}'
    )
    parser.add_argument(
        '--kernel',
        help='Path to kernel JSON file (optional, for device context)'
    )
    parser.add_argument(
        '--reasoning',
        help='Path to reasoning markdown file (optional)'
    )
    parser.add_argument(
        '--output', 
        default='./outputs',
        help='Output directory base (default: ./outputs)'
    )
    
    args = parser.parse_args()
    
    # Validate transcript path
    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"ERROR: Transcript not found: {transcript_path}")
        sys.exit(1)
    
    # Load transcript
    print(f"\n{'='*60}")
    print(f"LOADING TRANSCRIPT")
    print(f"{'='*60}")
    
    with open(transcript_path, 'r') as f:
        transcript_data = json.load(f)
    
    student_name = transcript_data.get('student_name', 'Unknown')
    assignment = transcript_data.get('assignment', 'Unknown')
    transcription = transcript_data.get('transcription', '')
    
    print(f"Student: {student_name}")
    print(f"Assignment: {assignment}")
    print(f"Words: {len(transcription.split())}")
    
    # Get evaluator
    print(f"\n{'='*60}")
    print(f"EVALUATING with {args.evaluator.upper()}")
    print(f"{'='*60}")
    
    EvaluatorClass = get_evaluator(args.evaluator)
    evaluator = EvaluatorClass()
    
    # Load kernel if provided
    if args.kernel:
        if not Path(args.kernel).exists():
            print(f"ERROR: Kernel not found: {args.kernel}")
            sys.exit(1)
        evaluator.load_kernel_context(args.kernel)
    
    # Load reasoning if provided
    if args.reasoning:
        if not Path(args.reasoning).exists():
            print(f"ERROR: Reasoning file not found: {args.reasoning}")
            sys.exit(1)
        evaluator.load_reasoning_context(args.reasoning)
    
    # Run evaluation
    result = evaluator.evaluate(
        {'transcription': transcription},
        kernel_path=args.kernel,
        reasoning_path=args.reasoning
    )
    
    # Print scores
    print(f"\n✓ Evaluation complete")
    print(f"  SM1: {result.sm1_score}/5 (ceiling {result.ceiling})")
    print(f"  SM2: {result.sm2_score}/5")
    print(f"  SM3: {result.sm3_score}/5")
    print(f"  Overall: {result.overall_score:.1f}/5 ({result.total_points:.1f}/25)")
    
    # Save evaluation
    output_base = Path(args.output)
    eval_dir = output_base / "evaluations"
    report_dir = output_base / "reports"
    eval_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = student_name.replace(' ', '_')
    safe_assignment = assignment.replace(' ', '_')
    
    # Save evaluation JSON
    eval_path = eval_dir / f"{safe_name}_{safe_assignment}_{args.evaluator}_evaluation.json"
    eval_data = {
        'student': student_name,
        'assignment': assignment,
        'evaluator': args.evaluator,
        'scores': {
            'sm1': result.sm1_score,
            'sm2': result.sm2_score,
            'sm3': result.sm3_score,
            'overall': result.overall_score,
            'total_points': result.total_points,
            'ceiling': result.ceiling
        },
        'components': {
            'topics': result.components.topics[:10],
            'verbs': result.components.verbs[:10],
            'objects': result.components.objects[:10],
            'detail_count': len(result.components.details),
            'effect_count': len(result.components.effects),
            'detail_quality': result.components.detail_quality
        },
        'feedback': result.feedback
    }
    
    with open(eval_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    # Save report
    report_path = report_dir / f"{safe_name}_{safe_assignment}_{args.evaluator}_report.md"
    percentage = (result.overall_score / 5 * 100)
    
    report = f"""# {args.evaluator.upper()} Report Card

**Student:** {student_name}  
**Assignment:** {assignment}  
**Overall Score:** {result.overall_score:.1f}/5 ({percentage:.0f}%)

---

## SM1 (Component Presence): {result.sm1_score}/5

**Current:** {result.feedback.get('sm1', 'N/A')}

**Next step:** {result.feedback.get('sm1_next', 'Continue developing specific textual details.')}

---

## SM2 (Density Performance): {result.sm2_score}/5

**Current:** {result.feedback.get('sm2', 'N/A')}

**Next step:** {result.feedback.get('sm2_next', 'Build more distinct insights.')}

---

## SM3 (Cohesion Performance): {result.sm3_score}/5

**Current:** {result.feedback.get('sm3', 'N/A')}

**Next step:** {result.feedback.get('sm3_next', 'Improve connectors and grammar.')}

---

*Generated by {args.evaluator} evaluator*
"""
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Summary
    print(f"\n{'='*60}")
    print("EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"Evaluation: {eval_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
