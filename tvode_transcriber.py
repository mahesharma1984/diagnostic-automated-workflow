#!/usr/bin/env python3
"""
TVODE Transcriber - Structured transcription with confidence scoring

Handles:
- Image to text conversion using Claude API
- Uncertainty detection (unclear words, strikethroughs)
- Confidence scoring
- Structured JSON output
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
        """Build structured transcription prompt"""
        
        prompt = f"""Transcribe this handwritten student work and return a structured JSON response.

**Student:** {student_name}
**Assignment:** {assignment}

**Instructions:**
1. Transcribe verbatim - preserve spelling errors and grammar mistakes (they're data for evaluation)
2. IGNORE any strikethrough text (crossed-out words)
3. Note any inserted or squeezed-in text
4. Flag unclear words with alternatives
5. Assess handwriting quality

**Return valid JSON only (no markdown, no backticks):**

{{
  "transcription": "Full verbatim text here...",
  "metadata": {{
    "word_count": 156,
    "handwriting_quality": "clear|moderate|difficult",
    "strikethroughs_present": true,
    "inserted_text_present": false
  }},
  "uncertainties": [
    {{
      "line_number": 5,
      "context": "...surrounding text...",
      "unclear_word": "word",
      "alternatives": ["word1", "word2"],
      "confidence": "low|medium|high",
      "reason": "why unclear"
    }}
  ],
  "notes": [
    "Line 3: crossed out 'axes', replaced with 'cues'",
    "Possible spelling error 'roll' vs 'role' at line 8"
  ]
}}

**Critical:** Return ONLY valid JSON. No explanatory text before or after."""

        return prompt
    
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
        
        # Convert dict uncertainties to Uncertainty objects (FIX FOR BUG)
        uncertainty_objects = [
            Uncertainty(
                line_number=u['line_number'],
                context=u['context'],
                unclear_word=u['unclear_word'],
                alternatives=u['alternatives'],
                confidence=u['confidence'],
                reason=u['reason']
            )
            for u in all_uncertainties
        ]
        
        # Calculate accuracy score
        accuracy_score = self._calculate_accuracy_score(
            uncertainty_objects,
            worst_handwriting,
            any_strikethroughs
        )
        
        # Determine if review needed
        requires_review = self._needs_review(uncertainty_objects, worst_handwriting, accuracy_score)
        
        result = TranscriptionResult(
            student_name=student_name,
            assignment=assignment,
            image_path=", ".join(image_paths),
            transcription=combined_transcription,
            word_count=total_word_count,
            handwriting_quality=worst_handwriting,
            strikethroughs_present=any_strikethroughs,
            uncertainties=uncertainty_objects,
            accuracy_score=accuracy_score,
            requires_review=requires_review,
            notes=all_notes
        )
        
        print(f"\n✓ All pages transcribed")
        print(f"  Total word count: {total_word_count}")
        print(f"  Handwriting: {worst_handwriting}")
        print(f"  Total uncertainties: {len(uncertainty_objects)}")
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
        
        # Build uncertainties for this page (keep as dicts for now)
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
        """Format uncertainties for targeted review"""
        
        if not result.requires_review:
            return "No review needed - auto-accepting transcription."
        
        output = f"\n{'▔'*60}\n"
        output += f"REVIEW NEEDED: {len(result.uncertainties)} uncertain section(s)\n"
        output += f"{'▔'*60}\n\n"
        
        for i, uncertainty in enumerate(result.uncertainties, 1):
            output += f"Section {i} (Line {uncertainty.line_number}):\n"
            output += f"  Context: \"{uncertainty.context}\"\n"
            output += f"  Unclear word: [{uncertainty.unclear_word}]\n"
            output += f"  Alternatives: {', '.join(uncertainty.alternatives)}\n"
            output += f"  Reason: {uncertainty.reason}\n"
            output += f"\n  Correction: _______\n"
            output += f"  (or press Enter to accept \"{uncertainty.unclear_word}\")\n\n"
        
        output += f"{'▔'*60}\n"
        output += f"Auto-accepting remaining {result.word_count - len(result.uncertainties)} words\n"
        output += f"{'▔'*60}\n"
        
        return output


def test_transcriber():
    """Test the transcriber"""
    
    # Test with Coden's Week 4 PDF
    test_file = "/mnt/user-data/uploads/Coden_-_week_4.pdf"
    
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return
    
    transcriber = TVODETranscriber()
    
    result = transcriber.transcribe(
        image_path=test_file,
        student_name="Coden",
        assignment="Week 4"
    )
    
    # Save result
    output_dir = Path("/mnt/user-data/outputs/transcripts")
    output_path = transcriber.save_result(result, output_dir)
    
    # Show review prompt if needed
    if result.requires_review:
        print(transcriber.format_review_prompt(result))
    
    print(f"\n{'='*60}")
    print("TRANSCRIPTION:")
    print(f"{'='*60}")
    print(result.transcription[:500] + "..." if len(result.transcription) > 500 else result.transcription)


if __name__ == "__main__":
    test_transcriber()
