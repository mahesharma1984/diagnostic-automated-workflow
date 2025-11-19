#!/usr/bin/env python3
"""
TVODE Evaluator - Programmatic Implementation of v3.3 Rubric

Converts rubric logic into code that can score transcripts automatically.
"""

import re
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TVODEComponents:
    """Extracted TVODE components from student writing"""
    topics: List[str]
    verbs: List[str]
    objects: List[str]
    details: List[str]
    effects: List[str]
    detail_quality: str  # "missing", "vague", "specific", "precise"


@dataclass
class EvaluationResult:
    """Complete evaluation output"""
    sm1_score: float
    sm2_score: float
    sm3_score: float
    overall_score: float
    total_points: float
    components: TVODEComponents
    feedback: Dict[str, str]
    ceiling: float


class TVODEEvaluator:
    """Programmatic evaluator implementing v3.3 rubric logic"""
    
    # Analytical verb patterns from rubric
    ANALYTICAL_VERBS = [
        'shows', 'reveals', 'creates', 'demonstrates', 'illustrates',
        'makes', 'causes', 'produces', 'establishes', 'builds',
        'questions', 'challenges', 'suggests', 'implies', 'indicates',
        'uses', 'employs', 'develops', 'constructs', 'presents'
    ]
    
    # Literary devices and topics
    LITERARY_TOPICS = [
        'narrator', 'narration', 'point of view', 'pov', 'perspective',
        'character', 'protagonist', 'author', 'lowry', 'fitzgerald',
        'tone', 'theme', 'conflict', 'resolution', 'setting',
        'metaphor', 'symbolism', 'irony', 'foreshadowing', 'imagery'
    ]
    
    # Effect indicators
    EFFECT_MARKERS = [
        'therefore', 'thus', 'so', 'as a result', 'consequently',
        'this shows', 'this reveals', 'this creates', 'this makes',
        'which', 'that', 'to'
    ]
    
    # Connectors for SM3
    CONNECTORS = [
        'therefore', 'thus', 'however', 'moreover', 'furthermore',
        'for example', 'for instance', 'in addition', 'consequently',
        'nevertheless', 'on the other hand', 'similarly', 'likewise'
    ]
    
    def __init__(self):
        pass
    
    # ==================== COMPONENT EXTRACTION ====================
    
    def extract_components(self, text: str) -> TVODEComponents:
        """Extract TVODE components from transcript text"""
        
        # Clean text
        text_lower = text.lower()
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        # Extract components
        topics = self._extract_topics(text_lower, sentences)
        verbs = self._extract_verbs(text_lower, sentences)
        objects = self._extract_objects(text_lower, sentences)
        details = self._extract_details(text, sentences)
        effects = self._extract_effects(text_lower, sentences)
        
        # Assess detail quality
        detail_quality = self._assess_detail_quality(details, text)
        
        return TVODEComponents(
            topics=topics,
            verbs=verbs,
            objects=objects,
            details=details,
            effects=effects,
            detail_quality=detail_quality
        )
    
    def _extract_topics(self, text_lower: str, sentences: List[str]) -> List[str]:
        """Extract Topic components (what's being analyzed)"""
        topics = []
        
        # Pattern 1: Literary devices/concepts
        for topic in self.LITERARY_TOPICS:
            if topic in text_lower:
                topics.append(topic)
        
        # Pattern 2: Character names (capitalized words)
        for sentence in sentences:
            words = sentence.split()
            for word in words:
                if word and word[0].isupper() and len(word) > 2:
                    if word.lower() not in ['the', 'this', 'that', 'chapter']:
                        topics.append(word)
        
        return list(set(topics))  # Remove duplicates
    
    def _extract_verbs(self, text_lower: str, sentences: List[str]) -> List[str]:
        """Extract analytical Verbs"""
        verbs = []
        
        for verb in self.ANALYTICAL_VERBS:
            if verb in text_lower:
                verbs.append(verb)
        
        return list(set(verbs))
    
    def _extract_objects(self, text_lower: str, sentences: List[str]) -> List[str]:
        """Extract Objects (what's affected by the analysis)"""
        objects = []
        
        # Pattern: "make/create the reader [verb]"
        reader_patterns = [
            r'(?:make|makes|create|creates|cause|causes)\s+(?:the\s+)?reader[s]?\s+(\w+)',
            r'reader[s]?\s+(?:to\s+)?(\w+)',
            r'(?:believe|question|understand|feel|think|realize)\s+(\w+)'
        ]
        
        for pattern in reader_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                if match.group(1):
                    objects.append(match.group(1))
        
        # Pattern: nouns after analytical verbs
        for sentence in sentences:
            for verb in self.ANALYTICAL_VERBS:
                if verb in sentence.lower():
                    # Extract words after verb
                    parts = sentence.lower().split(verb)
                    if len(parts) > 1:
                        words = parts[1].split()[:5]  # Next 5 words
                        objects.extend([w for w in words if len(w) > 3])
        
        return list(set(objects))
    
    def _extract_details(self, text: str, sentences: List[str]) -> List[str]:
        """Extract Details (textual evidence/quotes)"""
        details = []
        
        # Pattern 1: Quoted text
        quotes = re.findall(r'"([^"]+)"', text)
        details.extend(quotes)
        
        # Pattern 2: Phrases after "when", "through", "by", "with"
        detail_patterns = [
            r'when\s+([^,\.]+)',
            r'through\s+([^,\.]+)',
            r'by\s+([^,\.]+)',
            r'with\s+([^,\.]+)',
            r'since\s+([^,\.]+)',
            r'after\s+([^,\.]+)'
        ]
        
        for pattern in detail_patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                if match.group(1):
                    details.append(match.group(1).strip())
        
        return details
    
    def _extract_effects(self, text_lower: str, sentences: List[str]) -> List[str]:
        """Extract Effects (interpretive outcomes)"""
        effects = []
        
        # Pattern: Sentences containing effect markers
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for marker in self.EFFECT_MARKERS:
                if marker in sentence_lower:
                    effects.append(sentence.strip())
                    break
        
        return effects
    
    def _assess_detail_quality(self, details: List[str], full_text: str) -> str:
        """Assess Detail component quality per rubric criteria"""
        
        if not details:
            return "missing"
        
        # Check for specific details (quotes, precise descriptions)
        text_lower = full_text.lower()
        
        # Count vague phrases per rubric examples
        vague_phrases = [
            'careful language', 'curious about things', 'emotions and memories',
            'shows emotions', 'different things', 'special ability',
            'description are limited', 'no pain memory', 'make the reader'
        ]
        
        vague_count = sum(1 for phrase in vague_phrases if phrase in text_lower)
        
        # Check for quotes
        has_quotes = '"' in full_text
        quote_count = full_text.count('"') // 2
        
        # Check for analytical depth (not just quotes, but HOW quotes are used)
        analytical_connectors = ['which shows', 'which reveals', 'therefore', 'this shows']
        has_analysis = any(conn in text_lower for conn in analytical_connectors)
        
        # Rubric criteria:
        # - Precise (5): Quotes + analytical interpretation + no vague language
        # - Specific (4): Quotes + some context OR detailed descriptions
        # - Vague (3): General references without quotes or specifics
        
        if has_quotes and quote_count >= 2 and has_analysis and vague_count == 0:
            return "precise"
        elif has_quotes and quote_count >= 2:
            return "specific"
        elif has_quotes or (len(details) >= 3 and vague_count <= 1):
            return "specific"
        elif vague_count > 1:
            return "vague"
        else:
            return "vague"
    
    # ==================== SCORING LOGIC ====================
    
    def score_sm1(self, components: TVODEComponents) -> Tuple[float, float]:
        """Score Sub-Metric 1: Component Presence
        
        Returns: (score, ceiling)
        """
        
        # Count present components
        present = sum([
            len(components.topics) > 0,
            len(components.verbs) > 0,
            len(components.objects) > 0,
            len(components.details) > 0,
            len(components.effects) > 0
        ])
        
        # Apply rubric scoring logic
        if components.detail_quality == "precise" and present == 5:
            score = 5.0
            ceiling = 5.0
        elif components.detail_quality == "specific" and present >= 4:
            score = 4.0
            ceiling = 4.0
        elif components.detail_quality in ["vague", "specific"] and present >= 3:
            score = 3.0
            ceiling = 3.0
        elif present == 2:
            score = 2.0
            ceiling = 2.0
        else:
            score = 1.0
            ceiling = 2.0
        
        return score, ceiling
    
    def score_sm2(self, text: str, components: TVODEComponents, ceiling: float) -> float:
        """Score Sub-Metric 2: Density Performance
        
        Counts distinct analytical insights within ceiling constraint.
        """
        
        # Count distinct insights (non-repetitive analytical claims)
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        # Filter for analytical sentences (contain analytical verbs)
        analytical_sentences = []
        for sentence in sentences:
            if any(verb in sentence.lower() for verb in self.ANALYTICAL_VERBS):
                analytical_sentences.append(sentence)
        
        # Count distinct topics/claims across analytical sentences
        distinct_insights = self._count_distinct_insights(analytical_sentences, components)
        
        # Score within ceiling per rubric
        if ceiling == 3.0:
            # Vague details ceiling
            if distinct_insights >= 3:
                return 3.0  # Maximum extraction
            elif distinct_insights == 2:
                return 2.5
            elif distinct_insights == 1:
                return 2.0
            else:
                return 1.5
        
        elif ceiling == 4.0:
            # Specific details ceiling
            if distinct_insights >= 4:
                return 4.0
            elif distinct_insights == 3:
                return 3.5
            elif distinct_insights == 2:
                return 3.0
            else:
                return 2.5
        
        elif ceiling == 5.0:
            # Precise details ceiling
            if distinct_insights >= 5:
                return 5.0
            elif distinct_insights == 4:
                return 4.5
            else:
                return 4.0
        
        else:  # ceiling 2.0
            if distinct_insights >= 2:
                return 2.0
            else:
                return 1.0
    
    def _count_distinct_insights(self, sentences: List[str], components: TVODEComponents) -> int:
        """Count non-repetitive analytical insights"""
        
        if not sentences:
            return 0
        
        # More conservative approach: manually count different claims
        # Each paragraph typically makes 1 main insight
        paragraphs = len([s for s in sentences if len(s.split()) > 15])
        
        # Check for repetition - if same verb + object appears multiple times
        claim_patterns = set()
        for sentence in sentences:
            # Extract verb + object pattern
            for verb in components.verbs:
                for obj in components.objects:
                    if verb in sentence.lower() and obj in sentence.lower():
                        claim_patterns.add((verb, obj))
        
        # Conservative count: max of paragraph count or unique claim patterns, capped at 3
        distinct_count = min(max(paragraphs, len(claim_patterns)), 3)
        
        return max(distinct_count, 1)  # Minimum 1 insight
    
    def score_sm3(self, text: str, ceiling: float) -> float:
        """Score Sub-Metric 3: Cohesion Performance
        
        Assesses grammar, connectors, and organization within ceiling.
        """
        
        # Count connectors
        connector_count = sum(1 for conn in self.CONNECTORS if conn in text.lower())
        
        # Detect grammar errors
        grammar_errors = self._detect_grammar_errors(text)
        
        # Check organization (paragraphs, sections)
        has_organization = '\n\n' in text or text.count('\n') > 2
        
        # Score within ceiling
        if ceiling == 3.0:
            if grammar_errors <= 2 and connector_count >= 2:
                return 3.0
            elif grammar_errors <= 4 and connector_count >= 1:
                return 2.5
            else:
                return 2.0
        
        elif ceiling == 4.0:
            if grammar_errors <= 1 and connector_count >= 3 and has_organization:
                return 4.0
            elif grammar_errors <= 2 and connector_count >= 2:
                return 3.5
            else:
                return 3.0
        
        elif ceiling == 5.0:
            if grammar_errors == 0 and connector_count >= 4 and has_organization:
                return 5.0
            else:
                return 4.5
        
        else:  # ceiling 2.0
            if grammar_errors <= 5:
                return 2.0
            else:
                return 1.5
    
    def _detect_grammar_errors(self, text: str) -> int:
        """Simple grammar error detection (subject-verb agreement, fragments)"""
        
        errors = 0
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        # Pattern 1: Subject-verb agreement
        agreement_patterns = [
            r'\b(?:description|narrator|character|theme|conflict)\s+are\b',  # Singular + plural verb
            r'\b(?:descriptions|narrators|characters|themes)\s+is\b',  # Plural + singular verb
            r'\b(?:he|she|it|this|that)\s+(?:have|are|were|leave|make)\b',  # Singular pronoun + plural verb
            r'\b(?:they|we|these|those)\s+(?:has|is|was|leaves|makes)\b',  # Plural pronoun + singular verb
            r'\bpoint of view.*?leave\b'  # "point of view leave" should be "leaves"
        ]
        
        for pattern in agreement_patterns:
            errors += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Pattern 2: Awkward phrasing
        awkward_patterns = [
            r'feel more deep in',  # Should be "feel more deeply drawn into"
            r'make the reader to\s',  # Double infinitive
            r'makes reader\s',  # Missing article
        ]
        
        for pattern in awkward_patterns:
            errors += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Pattern 3: Very short fragments (< 3 words)
        for sentence in sentences:
            if len(sentence.split()) < 3 and sentence.lower() not in ['yes', 'no', 'okay']:
                errors += 1
        
        # Pattern 4: Run-ons (very long sentences without proper punctuation)
        for sentence in sentences:
            if len(sentence.split()) > 35 and sentence.count(',') < 2:
                errors += 0.5  # Count as half error
        
        return int(errors)
    
    # ==================== MAIN EVALUATION ====================
    
    def evaluate(self, transcript_json: Dict) -> EvaluationResult:
        """Main evaluation pipeline"""
        
        text = transcript_json.get('transcription', '')
        
        # Step 1: Extract components
        components = self.extract_components(text)
        
        # Step 2: Score SM1 and get ceiling
        sm1_score, ceiling = self.score_sm1(components)
        
        # Step 3: Score SM2 and SM3 within ceiling
        sm2_score = self.score_sm2(text, components, ceiling)
        sm3_score = self.score_sm3(text, ceiling)
        
        # Step 4: Calculate overall
        overall = (sm1_score * 0.4 + sm2_score * 0.3 + sm3_score * 0.3)
        total_points = overall * 5
        
        # Step 5: Generate feedback
        feedback = self._generate_feedback(components, sm1_score, sm2_score, sm3_score, text)
        
        return EvaluationResult(
            sm1_score=sm1_score,
            sm2_score=sm2_score,
            sm3_score=sm3_score,
            overall_score=overall,
            total_points=total_points,
            components=components,
            feedback=feedback,
            ceiling=ceiling
        )
    
    def _generate_feedback(self, components: TVODEComponents, sm1: float, sm2: float, sm3: float, text: str) -> Dict[str, str]:
        """Generate structured feedback per rubric template"""
        
        feedback = {}
        
        # SM1 feedback
        present_components = []
        if components.topics: present_components.append("Topic")
        if components.verbs: present_components.append("Verb")
        if components.objects: present_components.append("Object")
        if components.details: present_components.append("Detail")
        if components.effects: present_components.append("Effect")
        
        feedback['sm1'] = f"You have {', '.join(present_components)} components present. "
        feedback['sm1'] += f"Your Details are {components.detail_quality}."
        
        if components.detail_quality == "vague":
            feedback['sm1_next'] = "Add specific textual moments with exact quotes or actions instead of general descriptions."
        else:
            feedback['sm1_next'] = "Your specific details are good - now add more precise contextual information."
        
        # SM2 feedback
        sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
        analytical_count = sum(1 for s in sentences if any(v in s.lower() for v in self.ANALYTICAL_VERBS))
        
        feedback['sm2'] = f"You make {analytical_count} analytical attempts across your writing."
        feedback['sm2_next'] = "Build more distinct insights - each specific detail should unlock a DIFFERENT analytical point."
        
        # SM3 feedback
        connector_count = sum(1 for conn in self.CONNECTORS if conn in text.lower())
        grammar_errors = self._detect_grammar_errors(text)
        
        feedback['sm3'] = f"You use {connector_count} connectors and have approximately {grammar_errors} grammar issues."
        feedback['sm3_next'] = "Focus on subject-verb agreement and use more connectors like 'therefore' and 'which' to link ideas."
        
        return feedback
    
    # ==================== OUTPUT FORMATTING ====================
    
    def format_report_card(self, result: EvaluationResult, student_name: str) -> str:
        """Generate simplified report card"""
        
        report = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TVODE REPORT CARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Student: {student_name}
Score: {result.total_points:.1f}/25 ({result.overall_score:.1f}/5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sub-Metrics:
  SM1 (Component Presence):  {result.sm1_score}/5
  SM2 (Density Performance): {result.sm2_score}/5
  SM3 (Cohesion Performance): {result.sm3_score}/5

One-Line Summary:
  {result.feedback['sm1']} {result.feedback['sm2']}

One-Line Correction:
  {result.feedback['sm1_next']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report


# ==================== TESTING FUNCTION ====================

def test_evaluator():
    """Test the evaluator with Coden's Week 4 transcript"""
    
    # Coden's corrected transcript
    transcript = {
        "student_name": "Coden",
        "assignment": "Week 4",
        "transcription": """# Week 4 Homework

## Third person point of view:

In Chapter 11, Lowry uses third person limited point of view to make the reader question how the Giver feels when transmitting the memory since the description are limited on Jonas. "He breathed again, feeling the sharp intake of frigid air." "He could feel cold air swirling around his entire body." All of these description are limited on Jonas and none of them are about "The Giver". This third person limited point of view therefore, leave a mystery about 'The Giver' behind in this story.

## Reliable narrator:

In Chapter 11, Lowry uses reliable narrator to make the readers believe in the process of the transmission of the memory instead of thinking Jonas is drunk and just making stuff up. Jonas had a lot of questions after experiencing the sled, "Why don't we have snow, sled, and 'hills'?" "And when did we, in the past?" And a lot more, normally people would have a lot of questions after experiencing something new. Therefore, this reliable narrator makes the reader to believe Jonas had experienced everything and feel more deep in to the story."""
    }
    
    evaluator = TVODEEvaluator()
    result = evaluator.evaluate(transcript)
    
    # Print results
    print("\n" + "="*60)
    print("PROGRAMMATIC EVALUATION RESULTS")
    print("="*60)
    print(f"\nStudent: {transcript['student_name']}")
    print(f"Assignment: {transcript['assignment']}")
    print(f"\nScores:")
    print(f"  SM1: {result.sm1_score}/5 (Ceiling: {result.ceiling})")
    print(f"  SM2: {result.sm2_score}/5")
    print(f"  SM3: {result.sm3_score}/5")
    print(f"  Overall: {result.overall_score:.2f}/5 ({result.total_points:.1f}/25)")
    
    print(f"\nComponents Found:")
    print(f"  Topics: {result.components.topics[:5]}")
    print(f"  Verbs: {result.components.verbs[:5]}")
    print(f"  Objects: {result.components.objects[:5]}")
    print(f"  Details: {len(result.components.details)} items")
    print(f"  Effects: {len(result.components.effects)} items")
    print(f"  Detail Quality: {result.components.detail_quality}")
    
    print(f"\nFeedback:")
    for key, value in result.feedback.items():
        print(f"  {key}: {value}")
    
    print("\n" + evaluator.format_report_card(result, transcript['student_name']))


if __name__ == "__main__":
    test_evaluator()
