#!/usr/bin/env python3
"""
TVODE Transcriber - Structured transcription with confidence scoring

VERSION 2.0 - Conservative prompt to prevent hallucinations

Handles:
- Image to text conversion using Claude API
- Uncertainty detection (unclear words, strikethroughs)
- Confidence scoring
- Structured JSON output

CRITICAL CHANGE (v2.0):
- New conservative prompt prevents AI from inferring/guessing unclear text
- AI must flag uncertain words as [UNCLEAR] instead of fabricating plausible text
- Explicit "do not use language understanding to fill gaps" rules
- 95% visual certainty threshold before transcribing
"""

import os
import sys
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from anthropic import Anthropic


@dataclass
class Uncertainty:
    """Represents an unclear section needing review"""
    line_number: int
    context: str
    unclear_word: str
    alternatives: List[str]
    confidence: str  # "high", "medium", "low"
    reason: str


@dataclass
class TranscriptionResult:
    """Complete transcription output"""
    student_name: str
    assignment: str
    image_path: str
    transcription: str
    word_count: int
    handwriting_quality: str  # "clear", "moderate", "difficult"
    strikethroughs_present: bool
    uncertainties: List[Uncertainty]
    accuracy_score: float  # 0.0-1.0
    requires_review: bool
    notes: List[str]


class TVODETranscriber:
    """Transcribes student handwriting using Claude API with structured output"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """Encode image to base64 and detect media type"""
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        
        # Detect media type from extension
        ext = Path(image_path).suffix.lower()
        media_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_types.get(ext, 'image/jpeg')
        
        return image_data, media_type
    
    def _build_transcription_prompt(self, student_name: str, assignment: str) -> str:
        """Build focused transcription prompt (v2.1 - simplified for accuracy)
        
        Key changes from v2.0:
        - Shorter prompt (20 lines vs 180)
        - Focus on accuracy over exhaustive rules
        - Combined with temperature=0 for deterministic output
        """
        
        return f"""Transcribe this handwritten student work exactly as written.

**Student:** {student_name}
**Assignment:** {assignment}

RULES:
1. Transcribe ONLY text you can clearly read - mark unclear words as [UNCLEAR: best_guess/alternative]
2. COMPLETELY SKIP any crossed-out/strikethrough text (do not include it at all)
3. Preserve all spelling and grammar errors exactly as the student wrote them
4. Include the header/title at the top

CRITICAL: Do NOT guess or infer unclear words from context. If you can't clearly see each letter, mark it [UNCLEAR].

OUTPUT FORMAT - Return ONLY valid JSON (no markdown, no backticks):

{{
  "transcription": "Full text with [UNCLEAR] markers where needed...",
  "metadata": {{
    "word_count": 123,
    "handwriting_quality": "clear|moderate|difficult",
    "strikethroughs_present": true
  }},
  "uncertainties": [
    {{
      "line_number": 5,
      "context": "...surrounding text...",
      "unclear_word": "[UNCLEAR: option1/option2]",
      "alternatives": ["option1", "option2"],
      "confidence": "low",
      "reason": "letters unclear"
    }}
  ],
  "notes": ["any observations about the handwriting"]
}}"""
    
    def transcribe(self, image_path, student_name: str, assignment: str) -> TranscriptionResult:
        """Transcribe image(s) and return structured result
        
        Args:
            image_path: Single path string or list of paths for multi-page documents
        """
        
        # Handle single or multiple images
        if isinstance(image_path, str):
            image_paths = [image_path]
        else:
            image_paths = list(image_path)
        
        print(f"\n{'='*60}")
        print(f"TRANSCRIBING: {student_name} - {assignment}")
        print(f"Pages: {len(image_paths)}")
        print(f"{'='*60}")
        
        # Transcribe all pages
        all_transcriptions = []
        all_uncertainties = []
        all_notes = []
        total_word_count = 0
        worst_handwriting = "clear"
        any_strikethroughs = False
        
        for i, path in enumerate(image_paths, 1):
            print(f"\nProcessing page {i}/{len(image_paths)}...")
            result = self._transcribe_single_page(path, student_name, assignment, page_num=i)
            
            all_transcriptions.append(result['transcription'])
            all_uncertainties.extend(result['uncertainties'])
            all_notes.extend(result['notes'])
            total_word_count += result['word_count']
            
            # Track worst quality
            quality_rank = {'clear': 0, 'moderate': 1, 'difficult': 2}
            if quality_rank.get(result['handwriting_quality'], 1) > quality_rank.get(worst_handwriting, 0):
                worst_handwriting = result['handwriting_quality']
            
            if result['strikethroughs_present']:
                any_strikethroughs = True
        
        # Combine all pages
        combined_transcription = "\n\n".join(all_transcriptions)
        
        # Calculate accuracy score
        accuracy_score = self._calculate_accuracy_score(
            all_uncertainties,
            worst_handwriting,
            any_strikethroughs
        )
        
        # Determine if review needed
        requires_review = self._needs_review(all_uncertainties, worst_handwriting, accuracy_score)
        
        result = TranscriptionResult(
            student_name=student_name,
            assignment=assignment,
            image_path=", ".join(image_paths),
            transcription=combined_transcription,
            word_count=total_word_count,
            handwriting_quality=worst_handwriting,
            strikethroughs_present=any_strikethroughs,
            uncertainties=all_uncertainties,
            accuracy_score=accuracy_score,
            requires_review=requires_review,
            notes=all_notes
        )
        
        print(f"\n✓ All pages transcribed")
        print(f"  Total word count: {total_word_count}")
        print(f"  Handwriting: {worst_handwriting}")
        print(f"  Total uncertainties: {len(all_uncertainties)}")
        print(f"  Accuracy: {accuracy_score:.1%}")
        print(f"  Review needed: {'YES' if requires_review else 'NO'}")
        
        return result
    
    def _transcribe_single_page(self, image_path: str, student_name: str, assignment: str, page_num: int) -> dict:
        """Transcribe a single page"""
        
        # Encode image
        image_data, media_type = self._encode_image(image_path)
        
        # Build prompt
        prompt = self._build_transcription_prompt(student_name, assignment)
        prompt += f"\n\n**This is page {page_num} of the assignment.**"
        
        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=0,  # Deterministic output for transcription accuracy
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )
        
        # Extract response
        response_text = response.content[0].text
        
        # Parse JSON (handle potential markdown wrapping)
        response_text = response_text.strip()
        if response_text.startswith("```"):
            # Strip markdown code blocks
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        try:
            data = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON response for page {page_num}")
            print(f"Response text: {response_text[:500]}")
            raise e
        
        # Build uncertainties for this page
        uncertainties = [
            {
                'line_number': u.get('line_number', 0),
                'context': u.get('context', ''),
                'unclear_word': u.get('unclear_word', ''),
                'alternatives': u.get('alternatives', []),
                'confidence': u.get('confidence', 'low'),
                'reason': u.get('reason', '')
            }
            for u in data.get('uncertainties', [])
        ]
        
        metadata = data.get('metadata', {})
        
        return {
            'transcription': data['transcription'],
            'word_count': metadata.get('word_count', len(data['transcription'].split())),
            'handwriting_quality': metadata.get('handwriting_quality', 'moderate'),
            'strikethroughs_present': metadata.get('strikethroughs_present', False),
            'uncertainties': uncertainties,
            'notes': data.get('notes', [])
        }
    
    def _calculate_accuracy_score(self, 
                                   uncertainties: List[Uncertainty],
                                   handwriting_quality: str,
                                   strikethroughs_present: bool) -> float:
        """Calculate confidence score (0.0-1.0)"""
        
        # Base score
        score = 1.0
        
        # Penalize for uncertainties (-5% each)
        score -= len(uncertainties) * 0.05
        
        # Penalize for handwriting quality
        quality_multipliers = {
            'clear': 1.0,
            'moderate': 0.95,
            'difficult': 0.85
        }
        score *= quality_multipliers.get(handwriting_quality, 0.9)
        
        # Small penalty if strikethroughs present (risk of misreading)
        if strikethroughs_present:
            score *= 0.95
        
        return max(0.0, min(1.0, score))
    
    def _needs_review(self, 
                      uncertainties: List[Uncertainty],
                      handwriting_quality: str,
                      accuracy_score: float) -> bool:
        """Determine if human review is needed"""
        
        # Auto-accept if:
        # - No uncertainties AND
        # - Clear/moderate handwriting AND
        # - Accuracy >= 90%
        
        if len(uncertainties) == 0 and handwriting_quality != 'difficult' and accuracy_score >= 0.90:
            return False
        
        # Targeted review if 1-2 uncertainties
        if len(uncertainties) <= 2 and handwriting_quality != 'difficult':
            return True
        
        # Full review if:
        # - 3+ uncertainties OR
        # - Difficult handwriting OR
        # - Accuracy < 80%
        
        return True
    
    def save_result(self, result: TranscriptionResult, output_dir: Path) -> Path:
        """Save transcription result to JSON file"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        safe_name = result.student_name.replace(' ', '_')
        safe_assignment = result.assignment.replace(' ', '_')
        filename = f"{safe_name}_{safe_assignment}_transcript.json"
        
        output_path = output_dir / filename
        
        # Convert to dict
        result_dict = asdict(result)
        
        # Save
        with open(output_path, 'w') as f:
            json.dump(result_dict, f, indent=2)
        
        print(f"\n✓ Saved to: {output_path}")
        
        return output_path
    
    def format_review_prompt(self, result: TranscriptionResult) -> str:
        """Format uncertainties for targeted review
        
        Note: Uncertainties may be dicts or Uncertainty objects depending on context.
        This method handles both formats.
        """
        
        if not result.requires_review:
            return "No review needed - auto-accepting transcription."
        
        output = f"\n{'═'*60}\n"
        output += f"REVIEW NEEDED: {len(result.uncertainties)} uncertain section(s)\n"
        output += f"{'═'*60}\n\n"
        
        for i, uncertainty in enumerate(result.uncertainties, 1):
            # Handle both dict and dataclass formats
            if isinstance(uncertainty, dict):
                line_num = uncertainty.get('line_number', 0)
                context = uncertainty.get('context', '')
                unclear = uncertainty.get('unclear_word', '')
                alts = uncertainty.get('alternatives', [])
                reason = uncertainty.get('reason', '')
            else:
                line_num = uncertainty.line_number
                context = uncertainty.context
                unclear = uncertainty.unclear_word
                alts = uncertainty.alternatives
                reason = uncertainty.reason
            
            output += f"Section {i} (Line {line_num}):\n"
            output += f"  Context: \"{context}\"\n"
            output += f"  Unclear word: [{unclear}]\n"
            output += f"  Alternatives: {', '.join(alts)}\n"
            output += f"  Reason: {reason}\n"
            output += f"\n  Correction: _______\n"
            output += f"  (or press Enter to accept \"{unclear}\")\n\n"
        
        output += f"{'═'*60}\n"
        output += f"Auto-accepting remaining {result.word_count - len(result.uncertainties)} words\n"
        output += f"{'═'*60}\n"
        
        return output


def test_transcriber():
    """Test the transcriber - not used in production workflow"""
    print("This test function is not used in production.")
    print("Use tvode_automation.py instead:")
    print('  python3 tvode_automation.py --image "file.jpg" --student "Name" --assignment "Week 4"')


if __name__ == "__main__":
    test_transcriber()
