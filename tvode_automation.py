#!/usr/bin/env python3
"""
TVODE Automation Pipeline

Complete workflow:
1. Transcribe handwritten work (tvode_transcriber.py)
2. Review transcription (interactive or auto-accept)
3. Evaluate against v3.3 rubric (tvode_evaluator.py)
4. Generate report card

Usage:
    python tvode_automation.py --image student.jpg --student "Name" --assignment "Week 4"
    python tvode_automation.py --batch images/*.jpg --skip-review
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Import our modules
from tvode_transcriber import TVODETranscriber, TranscriptionResult
from tvode_evaluator import TVODEEvaluator, EvaluationResult


class TVODEAutomation:
    """Complete TVODE diagnostic automation pipeline"""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("./outputs")
        self.transcripts_dir = self.output_dir / "transcripts"
        self.evaluations_dir = self.output_dir / "evaluations"
        self.reports_dir = self.output_dir / "report_cards"
        
        # Create directories
        for d in [self.transcripts_dir, self.evaluations_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.transcriber = TVODETranscriber()
        self.evaluator = TVODEEvaluator()
    
    def process_single(self, 
                       image_path,  # Can be string or list
                       student_name: str,
                       assignment: str,
                       skip_review: bool = False) -> Dict:
        """Process a single student submission through complete pipeline
        
        Args:
            image_path: Single path or list of paths for multi-page documents
        """
        
        print(f"\n{'='*70}")
        print(f"PROCESSING: {student_name} - {assignment}")
        print(f"{'='*70}")
        
        # Stage 1: Transcription
        print("\n[Stage 1/4] Transcribing...")
        transcript_result = self.transcriber.transcribe(
            image_path=image_path,
            student_name=student_name,
            assignment=assignment
        )
        
        # Save transcription
        transcript_path = self.transcriber.save_result(transcript_result, self.transcripts_dir)
        
        # Stage 2: Review
        print("\n[Stage 2/4] Review...")
        if transcript_result.requires_review and not skip_review:
            transcript_result = self._interactive_review(transcript_result)
        else:
            print("✓ Auto-accepting transcription")
        
        # Stage 3: Evaluation
        print("\n[Stage 3/4] Evaluating...")
        eval_result = self._evaluate_transcript(transcript_result)
        
        # Save evaluation
        eval_path = self._save_evaluation(eval_result, transcript_result)
        
        # Stage 4: Report Card
        print("\n[Stage 4/4] Generating report card...")
        report_path = self._generate_report_card(eval_result, transcript_result)
        
        print(f"\n{'='*70}")
        print("COMPLETE")
        print(f"{'='*70}")
        print(f"Files created:")
        print(f"  - {transcript_path}")
        print(f"  - {eval_path}")
        print(f"  - {report_path}")
        
        return {
            'student': student_name,
            'assignment': assignment,
            'transcript_path': str(transcript_path),
            'evaluation_path': str(eval_path),
            'report_path': str(report_path),
            'score': eval_result.overall_score
        }
    
    def _interactive_review(self, transcript: TranscriptionResult) -> TranscriptionResult:
        """Interactive review of uncertain sections"""
        
        print(self.transcriber.format_review_prompt(transcript))
        
        corrected_text = transcript.transcription
        
        for uncertainty in transcript.uncertainties:
            # Handle both dict and dataclass formats
            if isinstance(uncertainty, dict):
                line_num = uncertainty.get('line_number', 0)
                context = uncertainty.get('context', '')
                unclear = uncertainty.get('unclear_word', '')
                alts = uncertainty.get('alternatives', [])
            else:
                line_num = uncertainty.line_number
                context = uncertainty.context
                unclear = uncertainty.unclear_word
                alts = uncertainty.alternatives
            
            print(f"\nSection at line {line_num}:")
            print(f"Context: \"{context}\"")
            print(f"Current: [{unclear}]")
            print(f"Alternatives: {', '.join(alts)}")
            
            correction = input("\nCorrection (or Enter to keep): ").strip()
            
            if correction:
                # Replace in transcription
                corrected_text = corrected_text.replace(unclear, correction, 1)
                print(f"✓ Updated to: {correction}")
        
        # Update transcript
        transcript.transcription = corrected_text
        transcript.requires_review = False
        transcript.notes.append("Reviewed and corrected by human")
        
        return transcript
    
    def _evaluate_transcript(self, transcript: TranscriptionResult) -> EvaluationResult:
        """Evaluate transcription against v3.3 rubric"""
        
        # Convert to format expected by evaluator
        transcript_json = {
            'student_name': transcript.student_name,
            'assignment': transcript.assignment,
            'transcription': transcript.transcription
        }
        
        # Run evaluation
        result = self.evaluator.evaluate(transcript_json)
        
        print(f"\n✓ Evaluation complete")
        print(f"  SM1: {result.sm1_score}/5 (ceiling {result.ceiling})")
        print(f"  SM2: {result.sm2_score}/5")
        print(f"  SM3: {result.sm3_score}/5")
        print(f"  Overall: {result.overall_score:.1f}/5 ({result.total_points:.1f}/25)")
        
        return result
    
    def _save_evaluation(self, 
                         eval_result: EvaluationResult,
                         transcript: TranscriptionResult) -> Path:
        """Save detailed evaluation to JSON"""
        
        safe_name = transcript.student_name.replace(' ', '_')
        safe_assignment = transcript.assignment.replace(' ', '_')
        filename = f"{safe_name}_{safe_assignment}_evaluation.json"
        
        output_path = self.evaluations_dir / filename
        
        # Build evaluation data
        eval_data = {
            'student': transcript.student_name,
            'assignment': transcript.assignment,
            'scores': {
                'sm1': eval_result.sm1_score,
                'sm2': eval_result.sm2_score,
                'sm3': eval_result.sm3_score,
                'overall': eval_result.overall_score,
                'total_points': eval_result.total_points,
                'ceiling': eval_result.ceiling
            },
            'components': {
                'topics': eval_result.components.topics[:10],
                'verbs': eval_result.components.verbs[:10],
                'objects': eval_result.components.objects[:10],
                'detail_count': len(eval_result.components.details),
                'effect_count': len(eval_result.components.effects),
                'detail_quality': eval_result.components.detail_quality
            },
            'feedback': eval_result.feedback
        }
        
        with open(output_path, 'w') as f:
            json.dump(eval_data, f, indent=2)
        
        return output_path
    
    def _generate_report_card(self,
                              eval_result: EvaluationResult,
                              transcript: TranscriptionResult) -> Path:
        """Generate simplified report card"""
        
        safe_name = transcript.student_name.replace(' ', '_')
        safe_assignment = transcript.assignment.replace(' ', '_')
        filename = f"{safe_name}_{safe_assignment}_report.txt"
        
        output_path = self.reports_dir / filename
        
        # Format report card (clean, one-line per SM)
        percentage = (eval_result.overall_score / 5 * 100)
        
        report = f"""{'='*70}
TVODE REPORT CARD
{'='*70}

Student: {transcript.student_name}
Assignment: {transcript.assignment}
Overall Score: {eval_result.overall_score:.1f}/5 ({percentage:.0f}%)

{'─'*70}

SM1 (Component Presence): {eval_result.sm1_score}/5
  Current: {eval_result.feedback['sm1']}
  Next step: {eval_result.feedback.get('sm1_next', 'Continue developing specific textual details.')}

SM2 (Density Performance): {eval_result.sm2_score}/5
  Current: {eval_result.feedback['sm2']}
  Next step: {eval_result.feedback.get('sm2_next', 'Build more distinct insights.')}

SM3 (Cohesion Performance): {eval_result.sm3_score}/5
  Current: {eval_result.feedback['sm3']}
  Next step: {eval_result.feedback.get('sm3_next', 'Improve connectors and grammar.')}

{'='*70}
"""
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        # Also print to console
        print(report)
        
        return output_path
    
    def process_batch(self,
                      image_paths: List[str],
                      skip_review: bool = True) -> List[Dict]:
        """Process multiple submissions"""
        
        results = []
        
        for i, image_path in enumerate(image_paths, 1):
            print(f"\n{'#'*70}")
            print(f"BATCH PROCESSING: {i}/{len(image_paths)}")
            print(f"{'#'*70}")
            
            # Extract student name and assignment from filename
            filename = Path(image_path).stem
            parts = filename.split('_')
            
            if len(parts) >= 2:
                student_name = parts[0]
                assignment = '_'.join(parts[1:])
            else:
                student_name = filename
                assignment = "Unknown"
            
            try:
                result = self.process_single(
                    image_path=image_path,
                    student_name=student_name,
                    assignment=assignment,
                    skip_review=skip_review
                )
                results.append(result)
            except Exception as e:
                print(f"\n❌ ERROR processing {filename}: {e}")
                results.append({
                    'student': student_name,
                    'assignment': assignment,
                    'error': str(e)
                })
        
        # Print summary
        self._print_batch_summary(results)
        
        return results
    
    def _print_batch_summary(self, results: List[Dict]):
        """Print summary of batch processing"""
        
        print(f"\n{'='*70}")
        print("BATCH SUMMARY")
        print(f"{'='*70}\n")
        
        successful = [r for r in results if 'score' in r]
        failed = [r for r in results if 'error' in r]
        
        print(f"Total processed: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}\n")
        
        if successful:
            print("Scores:")
            for result in successful:
                print(f"  {result['student']:20s} - {result['assignment']:15s} - {result['score']:.1f}/5")
        
        if failed:
            print("\nFailed:")
            for result in failed:
                print(f"  {result['student']:20s} - {result.get('error', 'Unknown error')}")


def main():
    """CLI entry point"""
    
    parser = argparse.ArgumentParser(description='TVODE Diagnostic Automation')
    
    # Single file mode
    parser.add_argument('--image', nargs='+', help='Path(s) to student work image(s) - supports multiple pages')
    parser.add_argument('--student', help='Student name')
    parser.add_argument('--assignment', help='Assignment name (e.g., "Week 4")')
    
    # Batch mode
    parser.add_argument('--batch', nargs='+', help='Multiple image paths')
    parser.add_argument('--skip-review', action='store_true', help='Auto-accept transcriptions')
    
    # Output
    parser.add_argument('--output', default='./outputs', help='Output directory')
    
    args = parser.parse_args()
    
    # Initialize automation
    automation = TVODEAutomation(output_dir=Path(args.output))
    
    # Single file mode
    if args.image:
        if not args.student or not args.assignment:
            print("ERROR: --student and --assignment required for single file mode")
            sys.exit(1)
        
        automation.process_single(
            image_path=args.image,
            student_name=args.student,
            assignment=args.assignment,
            skip_review=args.skip_review
        )
    
    # Batch mode
    elif args.batch:
        automation.process_batch(
            image_paths=args.batch,
            skip_review=args.skip_review
        )
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
