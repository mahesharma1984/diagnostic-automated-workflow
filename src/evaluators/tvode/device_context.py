"""
Device Context - Kernel loading and device matching

Handles:
- Loading device definitions from kernel JSON
- Fuzzy matching student device names to kernel
- Getting combined context for a device
"""

import re
import json
import string
from typing import Dict, List, Tuple, Optional

from .taxonomies import DEVICE_ALIASES


class DeviceContext:
    """Manages kernel device data and matching"""
    
    def __init__(self):
        self.devices: Dict[str, dict] = {}  # device_name -> device data
        self.normalized_map: Dict[str, str] = {}  # normalized_name -> original_name
        self.macro_pattern: str = ""
        self.reasoning_context: Dict[str, str] = {}
    
    def load_kernel(self, kernel_path: str) -> None:
        """Load device definitions from kernel JSON"""
        
        with open(kernel_path, 'r') as f:
            kernel = json.load(f)
        
        for device in kernel.get('micro_devices', []):
            name = device.get('name', '')
            name_lower = name.lower()
            
            # Skip duplicates - keep first instance (primary definition)
            if name_lower in self.devices:
                continue
            
            # Store device data
            # IMPORTANT: Use pedagogical_function (has description) over function (has code like "Me")
            self.devices[name_lower] = {
                'name': name,
                'definition': device.get('definition', ''),
                'function': device.get('pedagogical_function', device.get('function', '')),
                'classification': device.get('classification', ''),
                'macro_role': device.get('macro_role', ''),
                'examples': device.get('examples', [])
            }
            
            # Build normalized lookup
            normalized = self._normalize(name)
            self.normalized_map[normalized] = name_lower
        
        # Extract macro pattern
        macro_data = kernel.get('macro_pattern', {})
        if isinstance(macro_data, dict):
            self.macro_pattern = macro_data.get('description', '')
        elif isinstance(macro_data, str):
            self.macro_pattern = macro_data
        
        print(f"✓ Loaded {len(self.devices)} devices from kernel")
        self._print_sample()
    
    def _print_sample(self) -> None:
        """Print sample device to verify loading"""
        if self.devices:
            name = list(self.devices.keys())[0]
            func = self.devices[name].get('function', '')[:60]
            print(f"  Sample: '{name}' → function: '{func}...'")
    
    def load_reasoning(self, reasoning_path: str) -> None:
        """Load reasoning excerpts from markdown doc"""
        
        with open(reasoning_path, 'r') as f:
            content = f.read()
        
        # Extract sections (## or ### headers)
        pattern = r'###?\s+(.+?)\n(.+?)(?=\n###?|\Z)'
        for match in re.findall(pattern, content, re.DOTALL):
            device_name, reasoning = match
            self.reasoning_context[device_name.strip().lower()] = reasoning[:500].strip()
        
        print(f"✓ Loaded reasoning for {len(self.reasoning_context)} sections")
    
    def _normalize(self, name: str) -> str:
        """Normalize device name for matching"""
        
        result = name.lower()
        
        # Remove common suffixes
        for suffix in ['point of view', 'pov', 'narrative', 'narration', 'device', 'technique']:
            if result.endswith(' ' + suffix) or result.endswith(suffix):
                result = result.replace(suffix, '').strip()
        
        # Remove punctuation
        result = result.translate(str.maketrans('', '', string.punctuation))
        
        # Collapse spaces
        return ' '.join(result.split())
    
    def _apply_alias(self, name: str) -> str:
        """Apply device name aliases"""
        normalized = self._normalize(name)
        for alias, canonical in DEVICE_ALIASES.items():
            if normalized == self._normalize(alias):
                return canonical
        return name
    
    def match_device(self, student_name: str) -> Tuple[Optional[str], float]:
        """
        Match student's device name to kernel device
        
        Returns: (matched_device_name, confidence) or (None, 0.0)
        """
        
        if not self.devices:
            return None, 0.0
        
        # Apply alias first
        aliased = self._apply_alias(student_name)
        if aliased != student_name:
            student_name = aliased
        
        student_lower = student_name.lower().strip()
        
        # Strategy 1: Exact match
        if student_lower in self.devices:
            return student_lower, 1.0
        
        # Strategy 2: Normalized match
        student_norm = self._normalize(student_name)
        if student_norm in self.normalized_map:
            return self.normalized_map[student_norm], 0.95
        
        # Strategy 3: Word overlap
        student_words = set(student_norm.split())
        if not student_words:
            return None, 0.0
        
        best_match = None
        best_conf = 0.0
        
        for norm_name, orig_name in self.normalized_map.items():
            kernel_words = set(norm_name.split())
            overlap = student_words & kernel_words
            ratio = len(overlap) / max(len(student_words), len(kernel_words))
            
            if ratio > best_conf and len(overlap) >= 2:
                best_match = orig_name
                best_conf = ratio * 0.9
        
        if best_conf >= 0.5:
            return best_match, best_conf
        
        return None, 0.0
    
    def identify_device(self, text: str, topics: List[str]) -> Optional[str]:
        """
        Identify which device student is analyzing
        
        Args:
            text: Full student text
            topics: Extracted topic components
            
        Returns: Device name or None
        """
        
        if not self.devices:
            return None
        
        text_lower = text.lower()
        
        # Step 1: Check topics
        for topic in topics:
            if len(topic) < 4:
                continue
            
            matched, conf = self.match_device(topic)
            if matched and conf >= 0.5:
                print(f"  [Device Match] '{matched}' from topic '{topic}' ({conf:.0%})")
                return matched
        
        # Step 2: Combined topics
        for i in range(len(topics) - 1):
            combined = f"{topics[i]} {topics[i+1]}"
            matched, conf = self.match_device(combined)
            if matched and conf >= 0.7:
                print(f"  [Device Match] '{matched}' from combined '{combined}' ({conf:.0%})")
                return matched
        
        # Step 3: Search in text body
        for device_name in self.devices.keys():
            if device_name in text_lower or self._normalize(device_name) in text_lower:
                print(f"  [Device Match] '{device_name}' in text body")
                return device_name
        
        # Step 4: Pattern matching
        patterns = [
            r'uses?\s+([a-z\s]{8,40}?)\s+(?:to|when|in|where)',
            r'employs?\s+([a-z\s]{8,40}?)\s+(?:to|when|in|where)',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text_lower):
                matched, conf = self.match_device(match.strip())
                if matched and conf >= 0.6:
                    print(f"  [Device Match] '{matched}' from pattern '{match}' ({conf:.0%})")
                    return matched
        
        return None
    
    def get_context(self, device_name: str) -> Optional[Dict]:
        """Get combined context for a device"""
        
        if not device_name or device_name not in self.devices:
            return None
        
        context = {'kernel': self.devices[device_name]}
        
        if device_name in self.reasoning_context:
            context['reasoning'] = self.reasoning_context[device_name]
        
        if self.macro_pattern:
            context['macro_pattern'] = self.macro_pattern
        
        return context
    
    def get_function(self, device_name: str) -> str:
        """Get device function text (convenience method)"""
        if device_name and device_name in self.devices:
            return self.devices[device_name].get('function', '')
        return ''
    
    def get_definition(self, device_name: str) -> str:
        """Get device definition (convenience method)"""
        if device_name and device_name in self.devices:
            return self.devices[device_name].get('definition', '')
        return ''
