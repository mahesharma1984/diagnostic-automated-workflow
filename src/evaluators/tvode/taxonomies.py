"""
TVODE Taxonomies - Static classification data

Contains:
- Verb tiers (Tier 1-3 for analytical sophistication)
- Effect tiers (Tier 1-5 for meaning production)
- Connector types (for cohesion tracking)
- Literary topics (device/concept keywords)
"""

# ==================== VERB TAXONOMY ====================

VERB_TIERS = {
    'tier_1': {
        'verbs': [
            'creates', 'reveals', 'demonstrates', 'challenges',
            'undermines', 'exposes', 'critiques', 'interrogates',
            'disrupts', 'subverts', 'constructs', 'deconstructs'
        ],
        'weight': 1.0,
        'label': 'Critical Analysis'
    },
    'tier_2': {
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
    'tier_3': {
        'verbs': [
            'is', 'are', 'was', 'were', 'has', 'have', 'had',
            'uses', 'employs', 'does', 'makes', 'gets',
            'becomes', 'seems', 'appears', 'looks', 'leave', 'leaves'
        ],
        'weight': 0.0,
        'label': 'Description/Summary'
    }
}

# ==================== EFFECT TAXONOMY ====================

EFFECT_TIERS = {
    'tier_1': {
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
    'tier_2': {
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
    'tier_3': {
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
    'tier_4': {
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
    'tier_5': {
        'patterns': [
            r'(?:this|it)\s+(?:is|was)\s+.*(?:important|significant|meaningful)\s*$',
            r'^(?:therefore|thus|so)\s*$',
            r'affects?\s+(?:the\s+reader|us)\s*$',
        ],
        'weight': 0.0,
        'label': 'Missing/Circular'
    }
}

# ==================== CONNECTOR TAXONOMY ====================

CONNECTOR_TYPES = {
    'addition': ['furthermore', 'moreover', 'additionally', 'also', 'in addition', 'besides'],
    'contrast': ['however', 'nevertheless', 'whereas', 'although', 'yet', 'but', 'on the other hand', 'conversely'],
    'cause_effect': ['therefore', 'thus', 'consequently', 'hence', 'thereby', 'as a result', 'so'],
    'elaboration': ['which', 'whereby', 'wherein', 'through which', 'by which'],
    'exemplification': ['for example', 'for instance', 'specifically', 'such as', 'namely'],
    'summary': ['overall', 'in conclusion', 'ultimately', 'finally', 'in summary']
}

# ==================== LITERARY TOPICS ====================

LITERARY_TOPICS = [
    'narrator', 'narration', 'point of view', 'pov', 'perspective',
    'character', 'protagonist', 'author', 'lowry', 'fitzgerald',
    'tone', 'theme', 'conflict', 'resolution', 'setting',
    'metaphor', 'symbolism', 'irony', 'foreshadowing', 'imagery',
    'reliable narrator', 'unreliable narrator', 'third person', 'first person'
]

# ==================== DEVICE ALIASES ====================

DEVICE_ALIASES = {
    'first person': 'first-person narration',
    'second person': 'second-person narration',
    'third person': 'third-person limited',
    'third person omniscient': 'third-person omniscient',
    'pov': 'third-person limited',
    'reliable narrator': 'reliable narrator',
    'unreliable narrator': 'unreliable narrator',
    'fid': 'free indirect discourse',
    'stream of consciousness': 'stream of consciousness',
}


def build_verb_lookup():
    """Build flat verb -> (tier, weight, label) lookup"""
    lookup = {}
    for tier_name, tier_data in VERB_TIERS.items():
        for verb in tier_data['verbs']:
            lookup[verb] = (tier_name, tier_data['weight'], tier_data['label'])
    return lookup


# Pre-built lookup for performance
VERB_LOOKUP = build_verb_lookup()
