#!/usr/bin/env python3
"""
TVODE Evaluator v2.0 - Enhanced with Option A Taxonomies

ENHANCEMENTS:
1. Tiered Verb Taxonomy (Tier 1-3 for analytical sophistication)
2. Detail Quality Decision Tree (4.0, 4.25, 4.5, 4.75, 5.0 granularity)
3. Effect Taxonomy (Tier 1-5 for meaning production quality)
4. Connector Function Classification (variety tracking)

Based on v3.3 Rubric + V2 Requirements analysis
"""

import re
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class TVODEComponents:
    """Extracted TVODE components from student writing"""
    topics: List[str]
    verbs: List[str]
    objects: List[str]
    details: List[str]
    effects: List[str]
    detail_quality: str  # "missing", "vague", "specific", "precise"
    
    # Enhanced tracking
    verb_tiers: Dict[str, List[str]] = field(default_factory=dict)
    effect_tiers: Dict[str, List[str]] = field(default_factory=dict)
    connector_types: Dict[str, List[str]] = field(default_factory=dict)
    detail_score: float = 0.0
    verb_quality_score: float = 0.0
    effect_quality_score: float = 0.0


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
    """Enhanced programmatic evaluator implementing v3.3 rubric + Option A taxonomies"""
    
    # ==================== OPTION A: TIERED VERB TAXONOMY ====================
    
    ANALYTICAL_VERBS = {
        'tier_1_strong': {
            'verbs': [
                'creates', 'reveals', 'demonstrates', 'challenges',
                'undermines', 'exposes', 'critiques', 'interrogates',
                'disrupts', 'subverts', 'constructs', 'deconstructs'
            ],
            'weight': 1.0,
            'label': 'Critical Analysis'
        },
        'tier_2_moderate': {
            'verbs': [
                'shows', 'indicates', 'suggests', 'implies',
                'reflects', 'illustrates', 'represents', 'conveys',
                'establishes', 'develops', 'presents', 'depicts',
                'portrays', 'allows', 'enables', 'helps', 'hints',
                'prepares', 'builds'
            ],
            'weight': 0.5,
            'label': 'Pattern Recognition'
        },
        'tier_3_weak': {
            'verbs': [
                'is', 'are', 'was', 'were', 'has', 'have', 'had',
                'uses', 'employs', 'does', 'makes', 'gets',
                'becomes', 'seems', 'appears', 'looks', 'leave', 'leaves'
            ],
            'weight': 0.0,
            'label': 'Description/Summary'
        }
    }
    
    # ==================== OPTION A: EFFECT TAXONOMY ====================
    
    EFFECT_TAXONOMY = {
        'tier_1_alignment': {
            'patterns': [
                r'produc(?:es|ing)\s+(?:reinforcing|tensioning|mediating)\s+alignment',
                r'creat(?:es|ing)\s+(?:reinforcing|tensioning)\s+alignment',
                r'generat(?:es|ing)\s+meaning\s+through',
                r'alignment\s+where',
                r'the\s+gap\s+between.*constitutes',
                r'productive\s+(?:mis)?alignment',
            ],
            'weight': 1.0,
            'label': 'Alignment-Based Analysis'
        },
        'tier_2_meaning': {
            'patterns': [
                r'reveal(?:s|ing)\s+(?:how|that|why)',
                r'expos(?:es|ing).*(?:system|pattern|contradiction)',
                r'demonstrat(?:es|ing)\s+(?:how|that)',
                r'enabl(?:es|ing)\s+readers?\s+to',
                r'forc(?:es|ing)\s+readers?\s+to',
                r'requir(?:es|ing)\s+readers?\s+to\s+construct',
                r'show(?:s|ing)\s+(?:how|that).*(?:work|function|construct)',
                r'suggest(?:s|ing)\s+(?:how|that|why)',
            ],
            'weight': 0.75,
            'label': 'Meaning Production'
        },
        'tier_3_reader': {
            'patterns': [
                r'makes?\s+(?:the\s+)?readers?\s+(?:feel|understand|question|recognize)',
                r'allows?\s+readers?\s+to',
                r'helps?\s+readers?\s+(?:understand|see|realize)',
                r'invit(?:es|ing)\s+readers?\s+to',
                r'encourag(?:es|ing)\s+readers?\s+to',
                r'(?:focus|concentrat)(?:es|ing)\s+on',
            ],
            'weight': 0.5,
            'label': 'Reader Engagement'
        },
        'tier_4_generic': {
            'patterns': [
                r'makes?\s+(?:it|this|the\s+story)\s+(?:more\s+)?(?:interesting|engaging|meaningful)',
                r'creates?\s+(?:tension|suspense|interest|mystery)',
                r'shows?\s+(?:the|his|her)\s+(?:character|personality)',
                r'is\s+important\s+(?:to|for|because)',
                r'adds?\s+(?:depth|meaning|significance)',
            ],
            'weight': 0.25,
            'label': 'Generic Effect'
        },
        'tier_5_missing': {
            'patterns': [
                r'(?:this|it)\s+(?:is|was)\s+.*(?:important|significant|meaningful)\s*$',
                r'^(?:therefore|thus|so)\s*$',
                r'affects?\s+(?:the\s+reader|us)\s*$',
            ],
            'weight': 0.0,
            'label': 'Missing/Circular'
        }
    }
    
    # ==================== OPTION A: CONNECTOR CLASSIFICATION ====================
    
    CONNECTORS = {
        'addition': ['furthermore', 'moreover', 'additionally', 'also', 'in addition', 'besides'],
        'contrast': ['however', 'nevertheless', 'whereas', 'although', 'yet', 'but', 'on the other hand', 'conversely'],
        'cause_effect': ['therefore', 'thus', 'consequently', 'hence', 'thereby', 'as a result', 'so'],
        'elaboration': ['which', 'whereby', 'wherein', 'through which', 'by which'],
        'exemplification': ['for example', 'for instance', 'specifically', 'such as', 'namely'],
        'summary': ['overall', 'in conclusion', 'ultimately', 'finally', 'in summary']
    }
    
    # Literary devices and topics (unchanged)
    LITERARY_TOPICS = [
        'narrator', 'narration', 'point of view', 'pov', 'perspective',
        'character', 'protagonist', 'author', 'lowry', 'fitzgerald',
        'tone', 'theme', 'conflict', 'resolution', 'setting',
        'metaphor', 'symbolism', 'irony', 'foreshadowing', 'imagery',
        'reliable narrator', 'unreliable narrator', 'third person', 'first person'
    ]
    
    def __init__(self):
        # Flatten verb lists for quick lookup
        self.all_verbs = {}
        for tier_name, tier_data in self.ANALYTICAL_VERBS.items():
            for verb in tier_data['verbs']:
                self.all_verbs[verb] = (tier_name, tier_data['weight'], tier_data['label'])
    
    # ==================== COMPONENT EXTRACTION ====================
    
    def extract_components(self, text: str) -> TVODEComponents:
        """Extract TVODE components from transcript text with enhanced tracking"""
        
        # Clean text
        text_lower = text.lower()
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        # Extract components
        topics = self._extract_topics(text_lower, sentences)
        verbs, verb_tiers, verb_quality = self._extract_verbs_enhanced(text_lower, sentences)
        objects = self._extract_objects(text_lower, sentences)
        details = self._extract_details(text, sentences)
        effects, effect_tiers, effect_quality = self._extract_effects_enhanced(text, sentences)
        connector_types = self._extract_connectors_enhanced(text_lower)
        
        # Assess detail quality with decision tree
        detail_quality, detail_score = self._assess_detail_quality_v2(details, text)
        
        return TVODEComponents(
            topics=topics,
            verbs=verbs,
            objects=objects,
            details=details,
            effects=effects,
            detail_quality=detail_quality,
            verb_tiers=verb_tiers,
            effect_tiers=effect_tiers,
            connector_types=connector_types,
            detail_score=detail_score,
            verb_quality_score=verb_quality,
            effect_quality_score=effect_quality
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
                    if word.lower() not in ['the', 'this', 'that', 'chapter', 'in', 'and', 'for']:
                        topics.append(word)
        
        return list(set(topics))  # Remove duplicates
    
    def _extract_verbs_enhanced(self, text_lower: str, sentences: List[str]) -> Tuple[List[str], Dict, float]:
        """Extract analytical Verbs with tier classification"""
        verbs = []
        verb_tiers = {'tier_1': [], 'tier_2': [], 'tier_3': []}
        total_score = 0.0
        
        for verb_word, (tier, weight, label) in self.all_verbs.items():
            if verb_word in text_lower:
                verbs.append(verb_word)
                tier_key = tier.split('_')[0] + '_' + tier.split('_')[1]  # tier_1, tier_2, tier_3
                verb_tiers[tier_key].append(verb_word)
                total_score += weight
        
        return list(set(verbs)), verb_tiers, total_score
    
    def _extract_objects(self, text_lower: str, sentences: List[str]) -> List[str]:
        """Extract Objects (what's affected by the analysis)"""
        objects = []
        
        # Pattern: "make/create the reader [verb]"
        reader_patterns = [
            r'(?:make|makes|create|creates|cause|causes)\s+(?:the\s+)?readers?\s+(\w+)',
            r'readers?\s+(?:to\s+)?(\w+)',
            r'(?:believe|question|understand|feel|think|realize)\s+(\w+)'
        ]
        
        for pattern in reader_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                if match.group(1):
                    objects.append(match.group(1))
        
        # Pattern: nouns after analytical verbs
        for sentence in sentences:
            for verb in self.all_verbs.keys():
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
    
    def _extract_effects_enhanced(self, text: str, sentences: List[str]) -> Tuple[List[str], Dict, float]:
        """Extract Effects with tier classification"""
        effects = []
        effect_tiers = {'tier_1': [], 'tier_2': [], 'tier_3': [], 'tier_4': [], 'tier_5': []}
        total_score = 0.0
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            matched = False
            
            # Check each tier from highest to lowest
            for tier_name in ['tier_1_alignment', 'tier_2_meaning', 'tier_3_reader', 'tier_4_generic', 'tier_5_missing']:
                tier_data = self.EFFECT_TAXONOMY[tier_name]
                for pattern in tier_data['patterns']:
                    if re.search(pattern, sentence_lower):
                        effects.append(sentence.strip())
                        tier_key = tier_name.split('_')[0] + '_' + tier_name.split('_')[1]
                        effect_tiers[tier_key].append(sentence.strip())
                        total_score += tier_data['weight']
                        matched = True
                        break
                if matched:
                    break
        
        return effects, effect_tiers, total_score
    
    def _extract_connectors_enhanced(self, text_lower: str) -> Dict[str, List[str]]:
        """Extract connectors and classify by function"""
        connector_types = {}
        
        for func_type, connectors in self.CONNECTORS.items():
            found = []
            for conn in connectors:
                if conn in text_lower:
                    found.append(conn)
            if found:
                connector_types[func_type] = found
        
        return connector_types
    
    # ==================== OPTION A: DETAIL QUALITY DECISION TREE ====================
    
    def _assess_detail_quality_v2(self, details: List[str], text: str) -> Tuple[str, float]:
        """
        V2 Decision Tree for Detail Quality Assessment
        
        Returns: (quality_label, numeric_score)
        - 5.0: precise (quote + attribution + 4 context elements)
        - 4.75: precise (quote + attribution + 3 context)
        - 4.5: precise (quote + attribution + 2 context)
        - 4.25: specific (quote + attribution + 1 context)
        - 4.0: specific (quote without attribution OR paraphrase with visualization)
        - 3.0: vague (general descriptions)
        - 2.0: missing
        """
        
        if not details or len(details) == 0:
            return "missing", 2.0
        
        # Step 1: Check for direct quotes
        quotes = re.findall(r'"([^"]+)"', text)
        
        if not quotes:
            # Step 2: Paraphrase specificity check
            if self._can_visualize_moment(details, text):
                return "specific", 4.0
            else:
                return "vague", 3.0
        
        # Step 3: Quote quality check - has attribution?
        has_attribution = bool(re.search(r'(?:p\.|page)\s*\d+|chapter\s+\d+', text, re.I))
        
        if not has_attribution:
            return "specific", 4.0  # Quote without page context
        
        # Step 4: Contextual precision check (each adds 0.25)
        score = 4.0
        context_elements = 0
        
        if self._explains_when(text):
            score += 0.25
            context_elements += 1
        
        if self._explains_why(text):
            score += 0.25
            context_elements += 1
        
        if self._explains_how(text):
            score += 0.25
            context_elements += 1
        
        if self._explains_what_reveals(text):
            score += 0.25
            context_elements += 1
        
        # Determine label
        if score >= 4.75:
            return "precise", 5.0
        elif score >= 4.25:
            return "precise", score
        else:
            return "specific", score
    
    def _can_visualize_moment(self, details: List[str], text: str) -> bool:
        """Check if paraphrases are specific enough to visualize"""
        # Look for concrete nouns, sensory details, specific actions
        visualization_markers = [
            r'\b(?:eyes|face|hands|voice|body|snow|air|cold|warm|light|dark)\b',
            r'\b(?:walked|ran|felt|saw|heard|touched|breathed|looked)\b',
            r'\b(?:slowly|quickly|suddenly|carefully|gently|sharply)\b',
        ]
        
        text_lower = text.lower()
        marker_count = sum(1 for pattern in visualization_markers if re.search(pattern, text_lower))
        
        return marker_count >= 2
    
    def _explains_when(self, text: str) -> bool:
        """Check for temporal context"""
        when_patterns = [
            r'(?:when|after|before|during|while)\s+\w+',
            r'(?:in|at)\s+(?:chapter|page|the\s+beginning|the\s+end)',
        ]
        return any(re.search(p, text.lower()) for p in when_patterns)
    
    def _explains_why(self, text: str) -> bool:
        """Check for causal explanation"""
        why_patterns = [
            r'(?:because|since|due\s+to|as\s+a\s+result)',
            r'(?:to|in\s+order\s+to)\s+\w+',
        ]
        return any(re.search(p, text.lower()) for p in why_patterns)
    
    def _explains_how(self, text: str) -> bool:
        """Check for mechanism explanation"""
        how_patterns = [
            r'(?:by|through|via|using)\s+\w+',
            r'(?:with|without)\s+\w+',
        ]
        return any(re.search(p, text.lower()) for p in how_patterns)
    
    def _explains_what_reveals(self, text: str) -> bool:
        """Check for interpretive connection"""
        reveals_patterns = [
            r'(?:which|that|this)\s+(?:shows|reveals|demonstrates|suggests|indicates)',
            r'(?:revealing|showing|demonstrating)\s+(?:how|that|why)',
        ]
        return any(re.search(p, text.lower()) for p in reveals_patterns)
    
    # ==================== SCORING LOGIC ====================
    
    def score_sm1(self, components: TVODEComponents) -> Tuple[float, float]:
        """
        SM1: Component Presence + Detail Quality → Ceiling
        
        Enhanced to use:
        - Tier 1-2 verbs only (Tier 3 doesn't count as functional)
        - Detail decision tree score
        """
        
        # Count functional components
        has_topic = len(components.topics) > 0
        has_verb_functional = len(components.verb_tiers.get('tier_1', [])) > 0 or len(components.verb_tiers.get('tier_2', [])) > 0
        has_object = len(components.objects) > 0
        has_detail = len(components.details) > 0
        has_effect_functional = (
            len(components.effect_tiers.get('tier_1', [])) > 0 or
            len(components.effect_tiers.get('tier_2', [])) > 0 or
            len(components.effect_tiers.get('tier_3', [])) > 0
        )
        
        present_count = sum([has_topic, has_verb_functional, has_object, has_detail, has_effect_functional])
        
        # SM1 Score based on presence + detail quality
        detail_score = components.detail_score
        
        # Lookup table (from rubric)
        if present_count == 5 and detail_score >= 5.0:
            sm1 = 5.0
            ceiling = 5.0
        elif present_count == 5 and detail_score >= 4.5:
            sm1 = 4.5
            ceiling = 4.5
        elif present_count == 5 and detail_score >= 4.0:
            sm1 = 4.0
            ceiling = 4.0
        elif present_count >= 4 and detail_score >= 4.0:
            sm1 = 3.5
            ceiling = 4.0
        elif present_count >= 4 or detail_score >= 3.0:
            sm1 = 3.0
            ceiling = 3.0
        elif present_count >= 3:
            sm1 = 2.5
            ceiling = 3.0
        elif present_count >= 2:
            sm1 = 2.0
            ceiling = 2.5
        else:
            sm1 = 1.5
            ceiling = 2.0
        
        return sm1, ceiling
    
    def score_sm2(self, text: str, components: TVODEComponents, ceiling: float) -> float:
        """
        SM2: Density Performance (analytical attempts + quality)
        
        Enhanced to use:
        - Verb tier weighting for quality assessment
        - Effect tier weighting for depth assessment
        """
        
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        # Count analytical attempts (only Tier 1-2 verbs count)
        functional_verbs = set()
        for tier in ['tier_1', 'tier_2']:
            functional_verbs.update(components.verb_tiers.get(tier, []))
        
        analytical_count = 0
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(verb in sentence_lower for verb in functional_verbs):
                analytical_count += 1
        
        # Quality multiplier based on verb/effect sophistication
        avg_verb_tier = self._calculate_avg_tier(components.verb_tiers)
        avg_effect_tier = self._calculate_avg_tier(components.effect_tiers)
        
        quality_multiplier = (avg_verb_tier + avg_effect_tier) / 2
        
        # Adjusted distinct insights
        distinct_insights = analytical_count * quality_multiplier
        
        # Score based on density
        if distinct_insights >= 4:
            sm2_raw = 5.0
        elif distinct_insights >= 3:
            sm2_raw = 4.0
        elif distinct_insights >= 2:
            sm2_raw = 3.0
        elif distinct_insights >= 1:
            sm2_raw = 2.5
        else:
            sm2_raw = 2.0
        
        # Apply ceiling
        return min(sm2_raw, ceiling)
    
    def _calculate_avg_tier(self, tier_dict: Dict[str, List]) -> float:
        """Calculate average tier quality (1.0 = best, 0.0 = worst)"""
        weights = {
            'tier_1': 1.0,
            'tier_2': 0.75,
            'tier_3': 0.5,
            'tier_4': 0.25,
            'tier_5': 0.0
        }
        
        total_weight = 0.0
        total_count = 0
        
        for tier, items in tier_dict.items():
            count = len(items)
            if count > 0:
                weight = weights.get(tier, 0.0)
                total_weight += weight * count
                total_count += count
        
        return total_weight / total_count if total_count > 0 else 0.5
    
    def score_sm3(self, text: str, components: TVODEComponents, ceiling: float) -> float:
        """
        SM3: Cohesion Performance (connectors + grammar)
        
        Enhanced to use:
        - Connector variety bonus (not just count)
        """
        
        # Count unique connector types (not just total connectors)
        connector_count = sum(len(conns) for conns in components.connector_types.values())
        connector_variety = len(components.connector_types)
        
        # Variety bonus
        variety_bonus = connector_variety * 0.1
        effective_connectors = connector_count + variety_bonus
        
        # Grammar errors
        grammar_errors = self._detect_grammar_errors(text)
        
        # Score logic
        if effective_connectors >= 3 and grammar_errors <= 2:
            sm3_raw = 5.0
        elif effective_connectors >= 2 and grammar_errors <= 3:
            sm3_raw = 4.0
        elif effective_connectors >= 1 and grammar_errors <= 4:
            sm3_raw = 3.0
        elif grammar_errors <= 5:
            sm3_raw = 2.5
        else:
            sm3_raw = 2.0
        
        # Apply ceiling
        return min(sm3_raw, ceiling)
    
    def _detect_grammar_errors(self, text: str) -> int:
        """Simple grammar error detection (subject-verb agreement, fragments)"""
        
        errors = 0
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        # Pattern 1: Subject-verb agreement
        agreement_patterns = [
            r'\b(?:description|narrator|character|theme|conflict)\s+are\b',
            r'\b(?:descriptions|narrators|characters|themes)\s+is\b',
            r'\b(?:he|she|it|this|that)\s+(?:have|are|were|leave|make)\b',
            r'\b(?:they|we|these|those)\s+(?:has|is|was|leaves|makes)\b',
            r'\bpoint of view.*?leave\b'
        ]
        
        for pattern in agreement_patterns:
            errors += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Pattern 2: Awkward phrasing
        awkward_patterns = [
            r'feel more deep in',
            r'make the reader to\s',
            r'makes reader\s',
        ]
        
        for pattern in awkward_patterns:
            errors += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Pattern 3: Very short fragments
        for sentence in sentences:
            if len(sentence.split()) < 3 and sentence.lower() not in ['yes', 'no', 'okay']:
                errors += 1
        
        # Pattern 4: Run-ons
        for sentence in sentences:
            if len(sentence.split()) > 35 and sentence.count(',') < 2:
                errors += 0.5
        
        return int(errors)
    
    # ==================== MAIN EVALUATION ====================
    
    def evaluate(self, transcript_json: Dict) -> EvaluationResult:
        """Main evaluation pipeline"""
        
        text = transcript_json.get('transcription', '')
        
        # Step 1: Extract components with enhancements
        components = self.extract_components(text)
        
        # Step 2: Score SM1 and get ceiling
        sm1_score, ceiling = self.score_sm1(components)
        
        # Step 3: Score SM2 and SM3 within ceiling
        sm2_score = self.score_sm2(text, components, ceiling)
        sm3_score = self.score_sm3(text, components, ceiling)
        
        # Step 4: Calculate overall
        overall = (sm1_score * 0.4 + sm2_score * 0.3 + sm3_score * 0.3)
        total_points = overall * 5
        
        # Step 5: Generate enhanced feedback
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
        """Generate enhanced structured feedback with tier information"""
        
        feedback = {}
        
        # SM1 feedback with tier details
        present_components = []
        if components.topics: present_components.append("Topic")
        
        tier1_verbs = len(components.verb_tiers.get('tier_1', []))
        tier2_verbs = len(components.verb_tiers.get('tier_2', []))
        if tier1_verbs > 0 or tier2_verbs > 0:
            present_components.append(f"Verb (Tier 1: {tier1_verbs}, Tier 2: {tier2_verbs})")
        
        if components.objects: present_components.append("Object")
        if components.details: present_components.append("Detail")
        
        tier1_effects = len(components.effect_tiers.get('tier_1', []))
        tier2_effects = len(components.effect_tiers.get('tier_2', []))
        tier3_effects = len(components.effect_tiers.get('tier_3', []))
        if tier1_effects > 0 or tier2_effects > 0 or tier3_effects > 0:
            present_components.append(f"Effect (T1: {tier1_effects}, T2: {tier2_effects}, T3: {tier3_effects})")
        
        feedback['sm1'] = f"You have {', '.join(present_components)} components present. "
        feedback['sm1'] += f"Your Details are {components.detail_quality} ({components.detail_score:.2f}/5)."
        
        # Enhanced next steps based on weaknesses
        if components.detail_score < 4.0:
            feedback['sm1_next'] = "Add specific textual moments with exact quotes or actions instead of general descriptions."
        elif components.detail_score < 4.5:
            feedback['sm1_next'] = "Add page numbers and more contextual elements (when/why/how/what it reveals)."
        else:
            feedback['sm1_next'] = "Excellent detail precision! Maintain this level while expanding analytical depth."
        
        # Add verb improvement suggestions
        if tier1_verbs == 0:
            feedback['sm1_next'] += f" Try using Tier 1 verbs (reveals, creates, exposes, challenges) instead of Tier 3 verbs (uses, makes, has)."
        
        # SM2 feedback with quality assessment
        sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
        functional_verbs = set()
        for tier in ['tier_1', 'tier_2']:
            functional_verbs.update(components.verb_tiers.get(tier, []))
        
        analytical_count = sum(1 for s in sentences if any(v in s.lower() for v in functional_verbs))
        
        avg_effect_tier = self._calculate_avg_tier(components.effect_tiers)
        
        feedback['sm2'] = f"You make {analytical_count} analytical attempts. "
        if avg_effect_tier >= 0.75:
            feedback['sm2'] += "Your effects show strong meaning production awareness."
        elif avg_effect_tier >= 0.5:
            feedback['sm2'] += "Your effects focus on reader engagement."
        else:
            feedback['sm2'] += "Your effects are mostly generic."
        
        feedback['sm2_next'] = "Build more distinct insights - each specific detail should unlock a DIFFERENT analytical point."
        
        # Add effect improvement suggestions
        if tier1_effects == 0 and tier2_effects == 0:
            feedback['sm2_next'] += " Push toward meaning production effects: Instead of 'makes readers feel', explain HOW the device reveals/demonstrates deeper meaning."
        
        # SM3 feedback with variety tracking
        connector_variety = len(components.connector_types)
        total_connectors = sum(len(conns) for conns in components.connector_types.values())
        grammar_errors = self._detect_grammar_errors(text)
        
        feedback['sm3'] = f"You use {total_connectors} connectors across {connector_variety} types and have approximately {grammar_errors} grammar issues."
        
        if connector_variety <= 1:
            feedback['sm3_next'] = "Use more connector variety: Add contrast words (however, although) and cause-effect words (therefore, thus) alongside addition words."
        else:
            feedback['sm3_next'] = "Good connector variety! Focus on reducing grammar issues, especially subject-verb agreement."
        
        return feedback
    
    # ==================== OUTPUT FORMATTING ====================
    
    def format_report_card(self, result: EvaluationResult, student_name: str) -> str:
        """Generate enhanced report card with taxonomy details"""
        
        tier1_verbs = ', '.join(result.components.verb_tiers.get('tier_1', [])[:3]) or "None"
        tier2_verbs = ', '.join(result.components.verb_tiers.get('tier_2', [])[:3]) or "None"
        
        connector_types = ', '.join(result.components.connector_types.keys()) or "None"
        
        report = f"""
┌────────────────────────────────────────────────────────┐
  TVODE REPORT CARD v2.0 (Enhanced with Option A)
└────────────────────────────────────────────────────────┘
Student: {student_name}
Score: {result.total_points:.1f}/25 ({result.overall_score:.2f}/5)
────────────────────────────────────────────────────────

Sub-Metrics:
  SM1 (Component Presence):  {result.sm1_score}/5  [Ceiling: {result.ceiling}]
  SM2 (Density Performance): {result.sm2_score}/5
  SM3 (Cohesion Performance): {result.sm3_score}/5

Component Quality:
  Verb Quality: {result.components.verb_quality_score:.1f} pts
    - Tier 1 (Critical): {tier1_verbs}
    - Tier 2 (Moderate): {tier2_verbs}
  
  Detail Quality: {result.components.detail_score}/5 ({result.components.detail_quality})
  
  Effect Quality: {result.components.effect_quality_score:.1f} pts
  
  Connector Types: {connector_types}

One-Line Summary:
  {result.feedback['sm1']}

Next Steps:
  {result.feedback['sm1_next']}

────────────────────────────────────────────────────────
"""
        return report
    
    def export_json(self, result: EvaluationResult, student_name: str, assignment: str) -> Dict:
        """Export evaluation as JSON with full taxonomy data"""
        
        return {
            "student": student_name,
            "assignment": assignment,
            "scores": {
                "sm1": result.sm1_score,
                "sm2": result.sm2_score,
                "sm3": result.sm3_score,
                "overall": result.overall_score,
                "total_points": result.total_points,
                "ceiling": result.ceiling
            },
            "components": {
                "topics": result.components.topics[:10],
                "verbs": result.components.verbs[:10],
                "objects": result.components.objects[:10],
                "detail_count": len(result.components.details),
                "effect_count": len(result.components.effects),
                "detail_quality": result.components.detail_quality,
                "detail_score": result.components.detail_score,
                "verb_quality_score": result.components.verb_quality_score,
                "effect_quality_score": result.components.effect_quality_score,
                "verb_tiers": {k: len(v) for k, v in result.components.verb_tiers.items()},
                "effect_tiers": {k: len(v) for k, v in result.components.effect_tiers.items()},
                "connector_types": list(result.components.connector_types.keys())
            },
            "feedback": result.feedback
        }


# ==================== TESTING FUNCTION ====================

def test_evaluator():
    """Test the enhanced evaluator with Week 4 transcripts"""
    
    # Coden's Week 4 transcript (clean version)
    coden_data = {
        "student_name": "Coden",
        "assignment": "Week 4",
        "transcription": """Week 4 Homework

Third person point of view.
In Chapter 11, Lowry uses third person limited point of view to make the reader question how the giver feels when transmitting the memory since the descriptions are limited on Jonas. In "He breathed again, feeling the sharp intake of frigid air." "He could feel cold air swirling around his entire body." All of these description are limited on Jonas and none of them are about The Giver. This third person limited point of view therefore, leave a mystery about The Giver behind in this story.

Reliable narrator
In Chapter 11, Lowry uses reliable narrator to make the readers believe in the process of the transmission of memory instead of thinking Jonas is drunk and just making stuff up. Jonas had a lot of questions after experiencing the sled, "why don't we have snow, sled and hills." "And when did we, In the past?" And a lot more, normally people will have a lot of questions after experiencing something new. Therefore, this reliable narrator makes the readers believe Jonas had experienced everything and feel more deep into the story."""
    }
    
    evaluator = TVODEEvaluator()
    result = evaluator.evaluate(coden_data)
    
    # Print enhanced results
    print("\n" + "="*60)
    print("ENHANCED OPTION A EVALUATION RESULTS")
    print("="*60)
    print(evaluator.format_report_card(result, coden_data['student_name']))
    
    # Export JSON
    json_output = evaluator.export_json(result, coden_data['student_name'], coden_data['assignment'])
    print("\nJSON Output Preview:")
    print(json.dumps(json_output, indent=2)[:800] + "...")


if __name__ == "__main__":
    test_evaluator()
