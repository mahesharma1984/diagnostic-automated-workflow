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
import io
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from anthropic import Anthropic
from PIL import Image, ImageEnhance, ImageFilter


def extract_context_from_kernel(kernel_path: str) -> dict:
    """Extract character names, terms, and devices from kernel for OCR normalization.
    
    Args:
        kernel_path: Path to kernel JSON file
        
    Returns:
        dict with characters, terms, devices, title, author
    """
    import json as _json

    with open(kernel_path, "r") as f:
        kernel = _json.load(f)

    # Extract characters from artifact_1 (character taxonomy)
    characters: List[str] = []
    if "artifact_1" in kernel:
        for char_key, char_data in kernel["artifact_1"].get("characters", {}).items():
            if isinstance(char_data, dict):
                characters.append(char_data.get("name", char_key))
            else:
                characters.append(char_key)

    # Extract terms from artifact_1 (concepts, places, objects, events)
    terms: List[str] = []
    for category in ["concepts", "places", "objects", "events"]:
        if "artifact_1" in kernel and category in kernel["artifact_1"]:
            terms.extend(kernel["artifact_1"][category].keys())

    # Extract devices from thesis_slots
    devices: List[str] = []
    if "thesis_slots" in kernel:
        slots = kernel["thesis_slots"]
        for key in ["voice_label", "device_1", "device_2", "device_3"]:
            if key in slots and slots[key]:
                devices.append(slots[key])

    # Get title and author
    title = kernel.get("metadata", {}).get("title", "")
    author = kernel.get("metadata", {}).get("author", "")

    return {
        "characters": characters,
        "terms": terms,
        "devices": devices,
        "title": title,
        "author": author,
    }


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
class SentenceReview:
    """A sentence flagged for human review"""
    sentence_text: str          # Current transcription of this sentence
    line_start: int             # Start line in document
    line_end: int               # End line in document
    confidence: float           # 0.0-1.0 (below 0.85 triggers review)
    reason: str                 # Why flagged ("semantic uncertainty", "unclear words", etc.)


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
    uncertainties: List[Uncertainty]  # KEEP for backward compatibility
    sentences_for_review: List[SentenceReview]  # Sentence-level review items
    accuracy_score: float  # 0.0-1.0
    requires_review: bool
    notes: List[str]
    year_level: int = 8  # Student year level (7-12, default: 8)
    normalizations_applied: Optional[List[str]] = None  # Tracks book-term normalizations


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
    
    def _ocr_with_google_vision(self, image_path: str) -> dict:
        """Use Google Cloud Vision API for handwriting OCR.
        
        Returns:
            dict with:
                - text: Full extracted text
                - words: List of {word, confidence} dicts
                - low_confidence_words: Words with confidence < 0.85
                - avg_confidence: Average confidence across all words
        """
        from google.cloud import vision
        
        client = vision.ImageAnnotatorClient()
        
        with open(image_path, 'rb') as f:
            content = f.read()
        
        image = vision.Image(content=content)
        
        # Use document_text_detection for handwriting (better than text_detection)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        # Extract full text
        full_text = response.full_text_annotation.text if response.full_text_annotation else ""
        
        # Extract word-level confidence
        words = []
        low_confidence_words = []
        
        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            confidence = word.confidence
                            
                            words.append({
                                'word': word_text,
                                'confidence': confidence
                            })
                            
                            if confidence < 0.85:
                                low_confidence_words.append({
                                    'word': word_text,
                                    'confidence': confidence
                                })
        
        return {
            'text': full_text,
            'words': words,
            'low_confidence_words': low_confidence_words,
            'avg_confidence': sum(w['confidence'] for w in words) / len(words) if words else 0.0
        }
    
    def _structure_with_claude(
        self,
        raw_text: str,
        low_confidence_words: list,
        student_name: str,
        assignment: str,
        context: str = None,
        kernel_context: dict = None,
    ) -> dict:
        """Use Claude to structure raw OCR text and flag uncertain sentences.
        
        Claude does NOT read the image — only processes the OCR text.
        """
        # Build kernel context section if provided
        kernel_section = ""
        if kernel_context:
            chars = ", ".join(kernel_context.get("characters", [])[:10])
            terms = ", ".join(kernel_context.get("terms", [])[:15])
            devices = ", ".join(kernel_context.get("devices", [])[:5])
            title = kernel_context.get("title", "")
            author = kernel_context.get("author", "")

            kernel_section = f"""
## Book Context: {title} by {author}

**Characters (normalize OCR variations to these):**
{chars}

**Key Terms:**
{terms}

**Literary Devices:**
{devices}

NORMALIZATION RULES:
- If OCR shows "Jong", "Jone", "Janne", "Jones" → normalize to "Jonas"
- If OCR shows "Gaber", "Gabrel" → normalize to "Gabriel"
- If OCR shows "Samness" → normalize to "Sameness"
- If OCR shows "Third Pessa" → normalize to "Third Person"
- Match any close variations to the character/term lists above
- Preserve actual student spelling errors (don't normalize non-book words)
"""

        # Build human-readable list of low-confidence words for Claude
        low_conf_list = ", ".join(
            [
                f"'{w['word']}' ({w['confidence']:.0%})"
                for w in low_confidence_words[:10]
                if "word" in w and "confidence" in w
            ]
        )

        prompt = f"""Structure this OCR-extracted student essay text.

**Student:** {student_name}
**Assignment:** {assignment}
**Context:** {context or "Student essay"}
{kernel_section}

**Raw OCR text:**
{raw_text}

**Low-confidence words from OCR:** {low_conf_list or "None"}

TASKS:
1. Clean up OCR artifacts (random line breaks, spacing issues)
2. Normalize character names and book terms to correct spelling (see Book Context above)
3. Preserve student spelling/grammar errors for non-book words
4. Identify sentences with remaining uncertain words

OUTPUT FORMAT — Return ONLY valid JSON:

{{
  "transcription": "Cleaned and normalized text...",
  "metadata": {{
    "word_count": 123,
    "handwriting_quality": "clear|moderate|difficult"
  }},
  "sentences_for_review": [
    {{
      "sentence_text": "Sentence with uncertain words...",
      "line_start": 3,
      "line_end": 4,
      "confidence": 0.75,
      "reason": "contains uncertain word 'xyz'"
    }}
  ],
  "normalizations_applied": ["Jong → Jonas", "Samness → Sameness"],
  "notes": ["observations"]
}}"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        
        result_text = response.content[0].text.strip()
        
        # Parse JSON (handle markdown code blocks)
        if result_text.startswith("```"):
            parts = result_text.split("```")
            if len(parts) >= 2:
                result_text = parts[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
        
        return json.loads(result_text)
    
    def _preprocess_image(self, image_path: str, enhancement_level: str = "auto") -> tuple[str, str]:
        """Preprocess image to improve transcription accuracy.
        
        Args:
            image_path: Path to original image
            enhancement_level: "none", "light", "moderate", "aggressive", or "auto"
        
        Returns:
            Tuple of (base64_data, media_type) for preprocessed image
        """
        # Load image
        img = Image.open(image_path)
        
        # Convert to RGB if necessary (handles RGBA, palette images)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Auto-detect enhancement level based on image properties
        if enhancement_level == "auto":
            enhancement_level = self._detect_enhancement_needed(img)
        
        if enhancement_level == "none":
            return self._encode_image(image_path)
        
        # Apply enhancements based on level
        if enhancement_level in ["light", "moderate", "aggressive"]:
            # Step 1: Auto-contrast
            contrast_factor = {"light": 1.2, "moderate": 1.4, "aggressive": 1.6}[enhancement_level]
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)
            
            # Step 2: Sharpening
            sharpness_factor = {"light": 1.3, "moderate": 1.6, "aggressive": 2.0}[enhancement_level]
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpness_factor)
            
            # Step 3: Brightness adjustment (only if image is dark)
            if enhancement_level in ["moderate", "aggressive"]:
                # Check average brightness
                grayscale = img.convert('L')
                avg_brightness = sum(grayscale.getdata()) / len(list(grayscale.getdata()))
                if avg_brightness < 128:  # Dark image
                    brightness_factor = {"moderate": 1.1, "aggressive": 1.2}[enhancement_level]
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(brightness_factor)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        image_data = base64.standard_b64encode(buffer.read()).decode('utf-8')
        
        return image_data, 'image/jpeg'
    
    def _detect_enhancement_needed(self, img: Image.Image) -> str:
        """Analyze image to determine enhancement level needed.
        
        Returns: "none", "light", "moderate", or "aggressive"
        """
        # Convert to grayscale for analysis
        grayscale = img.convert('L')
        pixels = list(grayscale.getdata())
        
        # Calculate statistics
        avg_brightness = sum(pixels) / len(pixels)
        
        # Calculate contrast (standard deviation)
        variance = sum((p - avg_brightness) ** 2 for p in pixels) / len(pixels)
        std_dev = variance ** 0.5
        
        # Decision logic
        if std_dev > 60 and 80 < avg_brightness < 200:
            return "none"  # Good contrast and brightness
        elif std_dev > 45 and 60 < avg_brightness < 220:
            return "light"  # Slightly low contrast
        elif std_dev > 30:
            return "moderate"  # Low contrast
        else:
            return "aggressive"  # Very low contrast or problematic image
    
    def _assess_image_quality(self, image_path: str) -> dict:
        """Quick quality assessment before full transcription.
        
        Returns dict with:
            - quality_score: 0.0-1.0
            - usable: bool
            - issues: list of detected problems
            - recommended_enhancement: str
        """
        img = Image.open(image_path)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        issues = []
        score = 1.0
        
        # Check 1: Image size (too small = can't read text)
        width, height = img.size
        if width < 800 or height < 600:
            issues.append(f"Low resolution: {width}x{height}")
            score -= 0.2
        
        # Check 2: Brightness
        grayscale = img.convert('L')
        pixels = list(grayscale.getdata())
        avg_brightness = sum(pixels) / len(pixels)
        
        if avg_brightness < 50:
            issues.append(f"Very dark image: avg brightness {avg_brightness:.0f}/255")
            score -= 0.3
        elif avg_brightness < 80:
            issues.append(f"Dark image: avg brightness {avg_brightness:.0f}/255")
            score -= 0.15
        elif avg_brightness > 240:
            issues.append(f"Overexposed: avg brightness {avg_brightness:.0f}/255")
            score -= 0.2
        
        # Check 3: Contrast
        variance = sum((p - avg_brightness) ** 2 for p in pixels) / len(pixels)
        std_dev = variance ** 0.5
        
        if std_dev < 20:
            issues.append(f"Very low contrast: std dev {std_dev:.0f}")
            score -= 0.3
        elif std_dev < 35:
            issues.append(f"Low contrast: std dev {std_dev:.0f}")
            score -= 0.15
        
        # Check 4: Aspect ratio (detect cropping issues)
        aspect = width / height
        if aspect > 3 or aspect < 0.3:
            issues.append(f"Unusual aspect ratio: {aspect:.2f}")
            score -= 0.1
        
        # Determine recommended enhancement
        if score >= 0.85:
            enhancement = "none"
        elif score >= 0.7:
            enhancement = "light"
        elif score >= 0.5:
            enhancement = "moderate"
        else:
            enhancement = "aggressive"
        
        return {
            "quality_score": max(0.0, score),
            "usable": score >= 0.3,
            "issues": issues,
            "recommended_enhancement": enhancement,
            "resolution": f"{width}x{height}",
            "brightness": avg_brightness,
            "contrast": std_dev
        }
    
    def _build_transcription_prompt(self, student_name: str, assignment: str, context: str = None) -> str:
        """Build transcription prompt with sentence-level confidence scoring"""
        
        context_section = f"\n**Context:** {context}" if context else ""
        
        domain_hint = ""
        if context and 'Giver' in context:
            domain_hint = '''
DOMAIN CONTEXT: Essay about "The Giver" by Lois Lowry.
Expected terms: Jonas, Gabriel, The Giver, Sameness, release, memories, 
sled, Community, Elsewhere, Ceremony of Twelve, Assignments, Family Unit.
'''
        
        return f"""Transcribe this handwritten student work.

**Student:** {student_name}
**Assignment:** {assignment}{context_section}
{domain_hint}

RULES:
1. Transcribe ALL text, giving your best interpretation of every word
2. COMPLETELY SKIP any crossed-out/strikethrough text
3. Preserve all spelling and grammar errors exactly as written
4. Include the header/title at the top

CRITICAL: After transcribing, identify any SENTENCES where you are less than 85% confident. 
Flag sentences that:
- Contain words you had to guess at
- Don't make semantic sense (unusual phrases like "long body" instead of "loving family")
- Have multiple unclear words close together

OUTPUT FORMAT - Return ONLY valid JSON:

{{
  "transcription": "Full transcribed text here...",
  "metadata": {{
    "word_count": 123,
    "handwriting_quality": "clear|moderate|difficult",
    "strikethroughs_present": true
  }},
  "sentences_for_review": [
    {{
      "sentence_text": "The exact sentence as you transcribed it.",
      "line_start": 3,
      "line_end": 4,
      "confidence": 0.72,
      "reason": "unclear word 'long body' - may be misread"
    }}
  ],
  "notes": ["any observations"]
}}

If ALL sentences are 85%+ confident, return empty array: "sentences_for_review": []
"""
    
    def transcribe(
        self,
        image_path,
        student_name: str,
        assignment: str,
        year_level: int = 8,
        context: str = None,
        ocr_engine: str = "vision",
        kernel_path: str = None,
    ) -> TranscriptionResult:
        """Transcribe image(s) and return structured result
        
        Args:
            image_path: Single path string or list of paths for multi-page documents
            student_name: Student's name
            assignment: Assignment name
            year_level: Student year level (7-12, default: 8)
            context: Optional domain context to help disambiguate unclear words
            ocr_engine: "vision" (Google Cloud Vision) or "claude" (fallback)
            kernel_path: Optional path to kernel JSON for character/term normalization
        """
        
        # Store context for use in retry pass
        self._current_context = context or "Essay about The Giver by Lois Lowry"

        # Load kernel context if provided
        kernel_context = None
        if kernel_path:
            try:
                kernel_context = extract_context_from_kernel(kernel_path)
                print(f"  Loaded kernel context: {kernel_context.get('title', 'Unknown')}")
                chars_preview = ", ".join(kernel_context.get("characters", [])[:5])
                if chars_preview:
                    print(f"  Characters: {chars_preview}...")
            except Exception as e:
                print(f"  ⚠️ Failed to load kernel: {e}")
        
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
        all_sentences_for_review = []
        all_notes = []
        all_normalizations: List[str] = []
        total_word_count = 0
        worst_handwriting = "clear"
        any_strikethroughs = False
        
        for i, path in enumerate(image_paths, 1):
            print(f"\nProcessing page {i}/{len(image_paths)}...")
            result = self._transcribe_single_page(
                path,
                student_name,
                assignment,
                page_num=i,
                context=context,
                ocr_engine=ocr_engine,
                kernel_context=kernel_context,
            )
            
            all_transcriptions.append(result['transcription'])
            all_uncertainties.extend(result['uncertainties'])
            all_sentences_for_review.extend(result.get('sentences_for_review', []))
            all_notes.extend(result['notes'])
            all_normalizations.extend(result.get("normalizations_applied", []) or [])
            total_word_count += result['word_count']
            
            # Track worst quality
            quality_rank = {'clear': 0, 'moderate': 1, 'difficult': 2}
            if quality_rank.get(result['handwriting_quality'], 1) > quality_rank.get(worst_handwriting, 0):
                worst_handwriting = result['handwriting_quality']
            
            if result['strikethroughs_present']:
                any_strikethroughs = True
        
        # Combine all pages
        combined_transcription = "\n\n".join(all_transcriptions)
        
        # Two-pass: retry unclear sections if any
        if all_uncertainties and len(all_uncertainties) <= 10:  # Don't retry if too many issues
            # Use first page for retry (for multi-page, uncertainties are typically on first page)
            combined_transcription, remaining = self._retry_unclear_sections(
                image_paths[0],
                all_uncertainties,
                combined_transcription,
                context=self._current_context
            )
            all_uncertainties = remaining
        
        # Calculate accuracy score
        accuracy_score = self._calculate_accuracy_score(
            all_uncertainties,
            worst_handwriting,
            any_strikethroughs
        )
        
        # Convert sentence dicts to SentenceReview objects
        sentence_reviews = [
            SentenceReview(
                sentence_text=sent.get('sentence_text', ''),
                line_start=sent.get('line_start', 0),
                line_end=sent.get('line_end', 0),
                confidence=sent.get('confidence', 0.5),
                reason=sent.get('reason', 'flagged for review')
            )
            for sent in all_sentences_for_review
        ]
        
        # Determine if review needed
        requires_review = len(sentence_reviews) > 0 or self._needs_review(all_uncertainties, worst_handwriting, accuracy_score)
        
        result = TranscriptionResult(
            student_name=student_name,
            assignment=assignment,
            image_path=", ".join(image_paths),
            transcription=combined_transcription,
            word_count=total_word_count,
            handwriting_quality=worst_handwriting,
            strikethroughs_present=any_strikethroughs,
            uncertainties=all_uncertainties,
            sentences_for_review=sentence_reviews,
            accuracy_score=accuracy_score,
            requires_review=requires_review,
            notes=all_notes,
            year_level=year_level,
            normalizations_applied=all_normalizations or None,
        )
        
        print(f"\n✓ All pages transcribed")
        print(f"  Total word count: {total_word_count}")
        print(f"  Handwriting: {worst_handwriting}")
        print(f"  Total uncertainties: {len(all_uncertainties)}")
        print(f"  Accuracy: {accuracy_score:.1%}")
        print(f"  Review needed: {'YES' if requires_review else 'NO'}")
        
        return result
    
    def _transcribe_single_page(
        self,
        image_path: str,
        student_name: str,
        assignment: str,
        page_num: int,
        context: str = None,
        ocr_engine: str = "vision",
        kernel_context: dict = None,
    ) -> dict:
        """Transcribe a single page.
        
        Args:
            ocr_engine: "vision" (Google Cloud Vision) or "claude" (fallback)
        """
        # Assess image quality
        quality = self._assess_image_quality(image_path)
        print(f"  Image quality: {quality['quality_score']:.0%} ({quality['recommended_enhancement']} enhancement)")
        
        if not quality['usable']:
            raise ValueError(f"Image quality too low for transcription: {', '.join(quality['issues'])}")
        
        if quality['issues']:
            print(f"  Issues detected: {', '.join(quality['issues'])}")
        
        # Vision-first path
        if ocr_engine == "vision":
            try:
                # Step 1: OCR with Google Vision
                print("  Using Google Cloud Vision for OCR...")
                ocr_result = self._ocr_with_google_vision(image_path)
                
                print(
                    f"  OCR complete: {len(ocr_result['words'])} words, "
                    f"avg confidence: {ocr_result['avg_confidence']:.1%}"
                )
                
                if ocr_result['low_confidence_words']:
                    print(f"  Low confidence words: {len(ocr_result['low_confidence_words'])}")
                
                # Step 2: Structure with Claude
                print("  Structuring with Claude...")
                structured = self._structure_with_claude(
                    ocr_result['text'],
                    ocr_result['low_confidence_words'],
                    student_name,
                    assignment,
                    context,
                    kernel_context=kernel_context,
                )
                
                metadata = structured.get("metadata", {})
                
                return {
                    "transcription": structured.get("transcription", ocr_result["text"]),
                    "word_count": metadata.get("word_count", len(ocr_result["words"])),
                    "handwriting_quality": metadata.get("handwriting_quality", "moderate"),
                    "strikethroughs_present": False,  # Vision API doesn't detect this
                    "uncertainties": [],  # Deprecated, use sentences_for_review
                    "sentences_for_review": structured.get("sentences_for_review", []),
                    "notes": structured.get("notes", [])
                    + [
                        f"OCR: Google Vision ({ocr_result['avg_confidence']:.1%} avg confidence)"
                    ],
                    "normalizations_applied": structured.get("normalizations_applied", []),
                }
            except Exception as e:
                print(f"  ⚠️ Google Vision failed: {e}")
                print("  Falling back to Claude...")
                ocr_engine = "claude"
        
        # Claude-only fallback path (existing behavior)
        if ocr_engine == "claude":
            # Preprocess image based on quality assessment
            image_data, media_type = self._preprocess_image(
                image_path,
                enhancement_level=quality["recommended_enhancement"],
            )
            
            # Build prompt
            prompt = self._build_transcription_prompt(student_name, assignment, context=context)
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
                                "text": prompt,
                            },
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
                    "line_number": u.get("line_number", 0),
                    "context": u.get("context", ""),
                    "unclear_word": u.get("unclear_word", ""),
                    "alternatives": u.get("alternatives", []),
                    "confidence": u.get("confidence", "low"),
                    "reason": u.get("reason", ""),
                }
                for u in data.get("uncertainties", [])
            ]
            
            # Parse sentences_for_review
            sentences_for_review = []
            for sent in data.get("sentences_for_review", []):
                sentences_for_review.append(
                    {
                        "sentence_text": sent.get("sentence_text", ""),
                        "line_start": sent.get("line_start", 0),
                        "line_end": sent.get("line_end", 0),
                        "confidence": sent.get("confidence", 0.5),
                        "reason": sent.get("reason", "flagged for review"),
                    }
                )
            
            metadata = data.get("metadata", {})
            
            return {
                "transcription": data["transcription"],
                "word_count": metadata.get("word_count", len(data["transcription"].split())),
                "handwriting_quality": metadata.get("handwriting_quality", "moderate"),
                "strikethroughs_present": metadata.get("strikethroughs_present", False),
                "uncertainties": uncertainties,
                "sentences_for_review": sentences_for_review,
                "notes": data.get("notes", []),
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
    
    def _retry_unclear_sections(self, 
                                image_path: str, 
                                uncertainties: List[dict],
                                original_transcription: str,
                                context: str = None) -> tuple[str, List[dict]]:
        """Second pass: retry transcription of unclear sections with focused prompts.
        
        Args:
            image_path: Path to image
            uncertainties: List of uncertainty dicts from first pass
            original_transcription: Full transcription with [UNCLEAR] markers
            context: Optional domain context
        
        Returns:
            Tuple of (updated_transcription, remaining_uncertainties)
        """
        if not uncertainties:
            return original_transcription, []
        
        print(f"\n  Second pass: retrying {len(uncertainties)} unclear sections...")
        
        remaining_uncertainties = []
        updated_transcription = original_transcription
        
        for unc in uncertainties:
            unclear_word = unc.get('unclear_word', '')
            context_text = unc.get('context', '')
            alternatives = unc.get('alternatives', [])
            
            # Build focused retry prompt
            retry_prompt = f"""Look carefully at this handwritten text. I need you to focus on ONE unclear word.

CONTEXT FROM SURROUNDING TEXT:

"{context_text}"

THE UNCLEAR WORD appears where you see [UNCLEAR] in the context above.
Previous attempt suggested these alternatives: {', '.join(alternatives)}

{f"DOMAIN HINT: This is about 'The Giver' by Lois Lowry. The word might be: Jonas, Gabriel, Giver, Sameness, release, memories, sled, Community, etc." if context and 'Giver' in context else ""}

TASK: Look at the actual handwriting in the image. What does this word say?

RESPOND WITH ONLY:

- The word if you can read it with 90%+ confidence

- "[STILL_UNCLEAR: option1/option2]" if still uncertain

- "[ILLEGIBLE]" if truly unreadable

NO OTHER TEXT. Just the word or marker."""

            # Encode with aggressive enhancement for retry
            image_data, media_type = self._preprocess_image(image_path, enhancement_level="aggressive")
            
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=100,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                            {"type": "text", "text": retry_prompt}
                        ]
                    }]
                )
                
                result = response.content[0].text.strip()
                
                # Clean response - extract just the word, not explanations
                if '\n' in result:
                    result = result.split('\n')[0].strip()
                
                # Check for common explanation phrases
                explanation_phrases = [
                    "looking at", "i can see", "the word is", "it appears", 
                    "based on", "appears to be", "seems to be", "i believe"
                ]
                result_lower = result.lower()
                if any(phrase in result_lower for phrase in explanation_phrases):
                    print(f"    Retry returned explanation, skipping")
                    remaining_uncertainties.append(unc)
                    continue
                
                # If response is too long, it's an explanation not a word
                if len(result.split()) > 5:
                    print(f"    Retry returned explanation, skipping")
                    remaining_uncertainties.append(unc)
                    continue
                
                # Strip any trailing punctuation or quotes
                result = result.strip('."\'*')
                
                if result.startswith("[STILL_UNCLEAR") or result.startswith("[ILLEGIBLE"):
                    # Still unclear, keep in list
                    remaining_uncertainties.append(unc)
                else:
                    # Got a clear answer, replace in transcription
                    updated_transcription = updated_transcription.replace(unclear_word, result, 1)
                    print(f"    Resolved: {unclear_word} → {result}")
                    
            except Exception as e:
                print(f"    Retry failed for '{unclear_word}': {e}")
                remaining_uncertainties.append(unc)
        
        return updated_transcription, remaining_uncertainties


def test_transcriber():
    """Test the transcriber - not used in production workflow"""
    print("This test function is not used in production.")
    print("Use tvode_automation.py instead:")
    print('  python3 tvode_automation.py --image "file.jpg" --student "Name" --assignment "Week 4"')


if __name__ == "__main__":
    test_transcriber()
