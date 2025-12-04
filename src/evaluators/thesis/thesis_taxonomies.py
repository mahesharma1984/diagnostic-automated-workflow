"""
Thesis Taxonomies - Static classification data for DCCEPS argument assessment

Contains:
- Position markers (stance indicators)
- Evidence types (textual support classification)
- Reasoning patterns (logical connectors)
- Counter-argument signals
- DCCEPS layer indicators
"""

# ==================== POSITION MARKERS ====================

POSITION_MARKERS = {
    'strong_stance': {
        'patterns': [
            r'\b(?:I\s+)?(?:strongly\s+)?believe\s+(?:that\s+)?',
            r'\b(?:I\s+)?(?:am\s+)?convinced\s+(?:that\s+)?',
            r'\b(?:it\s+is\s+)?(?:clear|evident|obvious)\s+(?:that\s+)?',
            r'\bwithout\s+(?:a\s+)?doubt',
            r'\bdefinitely\b',
            r'\bclearly\b',
        ],
        'weight': 1.0,
        'label': 'Strong Stance'
    },
    'moderate_stance': {
        'patterns': [
            r'\b(?:I\s+)?(?:think|feel)\s+(?:that\s+)?',
            r'\b(?:in\s+my\s+)?opinion',
            r'\b(?:I\s+)?would\s+(?:say|argue)\s+(?:that\s+)?',
            r'\bto\s+me\b',
            r'\bwell\s+to\s+me\b',
            r'\bpersonally\b',
        ],
        'weight': 0.75,
        'label': 'Moderate Stance'
    },
    'hedged_stance': {
        'patterns': [
            r'\bmaybe\b',
            r'\bperhaps\b',
            r'\bmight\s+be\b',
            r'\bcould\s+be\b',
            r'\bsort\s+of\b',
            r'\bkind\s+of\b',
        ],
        'weight': 0.5,
        'label': 'Hedged Stance'
    },
    'implicit_stance': {
        'patterns': [
            r'\bis\s+more\s+(?:of\s+)?a\b',
            r'\bis\s+(?:a\s+)?(?:hero|victim)\b',
            r'\brather\s+than\b',
            r'\binstead\s+of\b',
        ],
        'weight': 0.6,
        'label': 'Implicit Stance'
    }
}

# ==================== EVIDENCE TYPES ====================

EVIDENCE_TYPES = {
    'specific_textual': {
        'patterns': [
            r'"[^"]{10,}"',  # Direct quotes 10+ chars
            r'(?:when|where)\s+(?:Jonas|he|she)\s+\w+',  # Specific scene references
            r'(?:chapter|scene|part)\s+(?:where|when)',
            r'(?:the\s+)?memory\s+of\s+\w+',  # "the memory of warfare"
            r'(?:the\s+)?moment\s+(?:when|where)',
        ],
        'weight': 1.0,
        'label': 'Specific Textual Evidence'
    },
    'paraphrased': {
        'patterns': [
            r'(?:this\s+is\s+shown|shown)\s+when',
            r'(?:we\s+)?(?:see|saw)\s+(?:this|that)\s+when',
            r'for\s+(?:example|instance)',
            r'such\s+as\s+when',
        ],
        'weight': 0.75,
        'label': 'Paraphrased Evidence'
    },
    'general_reference': {
        'patterns': [
            r'\bin\s+the\s+(?:book|story|novel|text)\b',
            r'\bthroughout\s+the\s+(?:book|story)\b',
            r'\bhe\s+(?:tried|attempted|wanted)\s+to\b',
            r'\bshe\s+(?:tried|attempted|wanted)\s+to\b',
        ],
        'weight': 0.5,
        'label': 'General Reference'
    },
    'assertion_only': {
        'patterns': [
            r'^(?:he|she|jonas|it)\s+(?:is|was)\s+',  # Starts with bare assertion
            r'\bbecause\s+(?:he|she|it)\s+(?:is|was)\b',  # Circular reasoning
        ],
        'weight': 0.25,
        'label': 'Assertion Without Evidence'
    }
}

# ==================== REASONING PATTERNS ====================

REASONING_PATTERNS = {
    'cause_effect': {
        'patterns': [
            r'\bbecause\b',
            r'\bsince\b',
            r'\btherefore\b',
            r'\bthus\b',
            r'\bas\s+a\s+result\b',
            r'\bconsequently\b',
            r'\bwhich\s+(?:means|shows|proves|demonstrates)\b',
            r'\bthis\s+(?:means|shows|proves|demonstrates)\b',
        ],
        'weight': 1.0,
        'label': 'Cause-Effect Reasoning'
    },
    'comparison': {
        'patterns': [
            r'\bmore\s+(?:of\s+a\s+)?(?:\w+)\s+than\b',
            r'\bless\s+(?:of\s+a\s+)?(?:\w+)\s+than\b',
            r'\brather\s+than\b',
            r'\binstead\s+of\b',
            r'\bunlike\b',
            r'\bcompared\s+to\b',
            r'\bwhile\s+(?:he|she|jonas)\b',
            r'\bwhereas\b',
        ],
        'weight': 0.75,
        'label': 'Comparative Reasoning'
    },
    'elaboration': {
        'patterns': [
            r'\bfurthermore\b',
            r'\bmoreover\b',
            r'\badditionally\b',
            r'\balso\b',
            r'\band\s+(?:he|she|this)\b',
        ],
        'weight': 0.5,
        'label': 'Elaboration'
    },
    'definition': {
        'patterns': [
            r'\b(?:a\s+)?(?:hero|victim)\s+(?:is|means)\b',
            r'\bwhat\s+(?:it\s+)?means\s+to\s+be\b',
            r'\bby\s+definition\b',
        ],
        'weight': 0.5,
        'label': 'Definition-Based'
    }
}

# ==================== COUNTER-ARGUMENT SIGNALS ====================

COUNTER_ARGUMENT_SIGNALS = {
    'explicit_acknowledgment': {
        'patterns': [
            r'\bon\s+(?:the\s+)?other\s+hand\b',
            r'\bhowever\b',
            r'\balthough\b',
            r'\beven\s+though\b',
            r'\bdespite\b',
            r'\bwhile\s+(?:it\s+is\s+)?true\s+that\b',
            r'\bsome\s+(?:might|may|could)\s+(?:say|argue)\b',
            r'\byou\s+(?:can|could)\s+(?:also\s+)?(?:say|argue|make\s+a\s+claim)\b',
        ],
        'weight': 1.0,
        'label': 'Explicit Counter-Acknowledgment'
    },
    'qualification': {
        'patterns': [
            r'\bbut\b',
            r'\byet\b',
            r'\bstill\b',
            r'\bnot\s+(?:really|entirely|completely)\b',
            r'\bmostly\b',
        ],
        'weight': 0.5,
        'label': 'Qualification'
    },
    'concession': {
        'patterns': [
            r'\b(?:he|she|jonas)\s+(?:is\s+)?also\s+(?:a\s+)?(?:hero|victim)\b',
            r'\bwe\s+(?:can\s+)?see\s+(?:that\s+)?(?:he|she)\s+is\s+both\b',
            r'\b(?:he|she)\s+(?:can\s+)?be\s+seen\s+as\s+both\b',
        ],
        'weight': 0.75,
        'label': 'Concession'
    }
}

# ==================== SYNTHESIS MARKERS ====================

SYNTHESIS_MARKERS = {
    'conclusive': {
        'patterns': [
            r'\btherefore\b.*\b(?:more|is)\s+(?:a\s+)?(?:hero|victim)\b',
            r'\bin\s+conclusion\b',
            r'\boverall\b',
            r'\bultimately\b',
            r'\bfinally\b',
            r'\bso\s+(?:I\s+)?(?:strongly\s+)?believe\b',
            r'\bthis\s+(?:is\s+)?why\b',
        ],
        'weight': 1.0,
        'label': 'Conclusive Synthesis'
    },
    'weighing': {
        'patterns': [
            r'\b(?:has\s+)?(?:suffered|saved|helped)\s+more\s+than\b',
            r'\boutweighs?\b',
            r'\b(?:the\s+)?evidence\s+(?:shows|suggests|proves)\b',
            r'\bcounting\s+(?:it\s+)?up\b',
            r'\bweighing\b',
        ],
        'weight': 0.75,
        'label': 'Evidence Weighing'
    }
}

# ==================== DCCEPS LAYER INDICATORS ====================

DCCEPS_LAYERS = {
    'definition': {
        'description': 'Identifies/labels without explanation',
        'indicators': ['is a', 'is more of a', 'can be seen as'],
        'weight': 1
    },
    'comparison': {
        'description': 'Distinguishes between alternatives',
        'indicators': ['more than', 'rather than', 'unlike', 'compared to'],
        'weight': 2
    },
    'cause_effect': {
        'description': 'Shows HOW components produce meaning',
        'indicators': ['because', 'therefore', 'which causes', 'resulting in', 'leads to'],
        'weight': 3
    },
    'problem_solution': {
        'description': 'Frames purpose/function of configuration',
        'indicators': ['in order to', 'the purpose', 'this allows', 'thereby achieving'],
        'weight': 4
    }
}


def build_position_lookup():
    """Build flat lookup for position markers"""
    lookup = {}
    for stance_type, data in POSITION_MARKERS.items():
        for pattern in data['patterns']:
            lookup[pattern] = (stance_type, data['weight'], data['label'])
    return lookup


def build_evidence_lookup():
    """Build flat lookup for evidence types"""
    lookup = {}
    for ev_type, data in EVIDENCE_TYPES.items():
        for pattern in data['patterns']:
            lookup[pattern] = (ev_type, data['weight'], data['label'])
    return lookup


# Pre-built lookups
POSITION_LOOKUP = build_position_lookup()
EVIDENCE_LOOKUP = build_evidence_lookup()





