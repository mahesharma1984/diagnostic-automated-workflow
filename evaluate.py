#!/usr/bin/env python3
"""
Evaluate CLI - Stage 2 of diagnostic pipeline

Evaluates a JSON transcript against a rubric and generates a report.
Uses Claude API for evaluation by default (more accurate).

Usage:
    python evaluate.py --transcript outputs/transcripts/Name_Week_4_transcript.json --evaluator tvode
    python evaluate.py --transcript transcript.json --evaluator tvode --kernel kernels/The_Giver.json
    python evaluate.py --transcript transcript.json --evaluator tvode --rule-based  # Use rule-based instead

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
    # Basic evaluation (API-based by default)
    python evaluate.py --transcript outputs/transcripts/Coden_Week_4_transcript.json --evaluator tvode
    
    # With kernel context
    python evaluate.py --transcript transcript.json --evaluator tvode --kernel kernels/The_Giver.json
    
    # API evaluation with custom API key
    python evaluate.py --transcript transcript.json --evaluator tvode --api-key sk-ant-...
    
    # Use rule-based evaluation (fallback)
    python evaluate.py --transcript transcript.json --evaluator tvode --rule-based
    
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
    parser.add_argument(
        '--rule-based',
        action='store_true',
        help='Use rule-based evaluation instead of API (API is default)'
    )
    parser.add_argument(
        '--api-key',
        help='Anthropic API key (optional, can also use ANTHROPIC_API_KEY env var)'
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
    if args.rule_based:
        print("  Using rule-based evaluation")
    else:
        print("  Using API-based evaluation (Claude)")
    print(f"{'='*60}")
    
    EvaluatorClass = get_evaluator(args.evaluator)
    evaluator = EvaluatorClass()
    
    # Load kernel if provided (only for TVODE evaluator)
    if args.kernel and args.evaluator != 'thesis':
        if not Path(args.kernel).exists():
            print(f"ERROR: Kernel not found: {args.kernel}")
            sys.exit(1)
        if hasattr(evaluator, 'load_kernel_context'):
            evaluator.load_kernel_context(args.kernel)
    
    # Load reasoning if provided (only for TVODE evaluator)
    if args.reasoning and args.evaluator != 'thesis':
        if not Path(args.reasoning).exists():
            print(f"ERROR: Reasoning file not found: {args.reasoning}")
            sys.exit(1)
        if hasattr(evaluator, 'load_reasoning_context'):
            evaluator.load_reasoning_context(args.reasoning)
    
    # Run evaluation
    # Handle different evaluator interfaces
    if args.evaluator == 'thesis':
        # Thesis evaluator accepts string directly
        result = evaluator.evaluate(transcription)
    else:
        # TVODE evaluator expects dict with additional params
        result = evaluator.evaluate(
            {'transcription': transcription},
            kernel_path=args.kernel,
            reasoning_path=args.reasoning,
            use_api=not args.rule_based,  # API is default, unless --rule-based is set
            api_key=args.api_key,
            use_rule_based=args.rule_based
        )
    
    # Print scores
    print(f"\n✓ Evaluation complete")
    print(f"  SM1: {result.sm1_score}/5 (ceiling {result.ceiling})")
    print(f"  SM2: {result.sm2_score}/5")
    print(f"  SM3: {result.sm3_score}/5")
    print(f"  Overall: {result.overall_score:.1f}/5 ({result.total_points:.1f}/25)")
    if args.evaluator == 'thesis' and hasattr(result, 'dcceps_layer'):
        print(f"  DCCEPS Layer: {result.dcceps_layer} ({result.dcceps_label})")
    
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
    
    # Build evaluation data based on evaluator type
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
        'feedback': result.feedback
    }
    
    # Add evaluator-specific data
    if args.evaluator == 'thesis':
        # Thesis evaluator structure
        eval_data['dcceps'] = {
            'layer': result.dcceps_layer,
            'label': result.dcceps_label
        }
        eval_data['components'] = {
            'position': result.components.position,
            'position_strength': result.components.position_strength,
            'evidence_quality': result.components.evidence_quality,
            'evidence_count': len(result.components.evidence_items),
            'reasoning_chains': len(result.components.reasoning_chains),
            'counter_arguments': len(result.components.counter_arguments),
            'has_synthesis': bool(result.components.synthesis)
        }
    else:
        # TVODE evaluator structure
        eval_data['components'] = {
            'topics': result.components.topics[:10],
            'verbs': result.components.verbs[:10],
            'objects': result.components.objects[:10],
            'detail_count': len(result.components.details),
            'effect_count': len(result.components.effects),
            'detail_quality': result.components.detail_quality
        }
        if hasattr(result, 'distinct_insights'):
            eval_data['sm2_analysis'] = {
                'distinct_insights': result.distinct_insights,
                'effect_dimensions': result.effect_dimensions
            }
        if hasattr(result, 'grammar_error_count'):
            eval_data['sm3_analysis'] = {
                'connector_types': len(result.components.connector_types),
                'grammar_error_count': result.grammar_error_count,
                'grammar_errors': result.grammar_errors
            }
    
    with open(eval_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    # Save report
    report_path = report_dir / f"{safe_name}_{safe_assignment}_{args.evaluator}_report.md"
    percentage = (result.overall_score / 5 * 100)
    
    # Generate report based on evaluator type
    if args.evaluator == 'thesis':
        report = f"""# Thesis Quality Report: {student_name}

**Overall Score:** {result.overall_score:.1f}/5 ({percentage:.0f}%)
**DCCEPS Layer Reached:** {result.dcceps_layer} ({result.dcceps_label})

---

## SM1: Position + Evidence ({result.sm1_score:.1f}/5)

{result.feedback.get('sm1', 'N/A')}

**Next Step:** {result.feedback.get('sm1_next', 'Continue developing position and evidence.')}

---

## SM2: Reasoning Depth ({result.sm2_score:.1f}/5)

{result.feedback.get('sm2', 'N/A')}

**Next Step:** {result.feedback.get('sm2_next', 'Build stronger reasoning chains.')}

---

## SM3: Argument Coherence ({result.sm3_score:.1f}/5)

{result.feedback.get('sm3', 'N/A')}

**Next Step:** {result.feedback.get('sm3_next', 'Improve argument coherence.')}

---

## DCCEPS Progress

{result.feedback.get('dcceps_guidance', 'Continue developing your argument.')}

---

*Score Formula: (SM1 × 0.40) + (SM2 × 0.30) + (SM3 × 0.30) × 5 = Total Points*
"""
    else:
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
