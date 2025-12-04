#!/usr/bin/env python3
"""
Patch existing transcript JSON files with year_level field

Usage:
    # Patch single file
    python3 patch_transcripts.py --file Desmond_Week5_transcript.json --year-level 8
    
    # Patch multiple files
    python3 patch_transcripts.py --files *.json --year-level 8
    
    # Patch all transcripts in a directory
    python3 patch_transcripts.py --dir ./transcripts --year-level 8
    
    # Patch with student-specific levels
    python3 patch_transcripts.py --mapping students.json
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional


def patch_transcript(filepath: Path, year_level: int, dry_run: bool = False) -> bool:
    """
    Add year_level field to a transcript JSON file
    
    Args:
        filepath: Path to transcript JSON
        year_level: Year level to add (7-12)
        dry_run: If True, print changes without writing
    
    Returns:
        True if patched successfully
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        old_level = data.get('year_level')
        data['year_level'] = year_level
        
        if dry_run:
            status = "would update" if old_level != year_level else "unchanged"
            print(f"  {filepath.name}: {status} (year_level: {old_level} → {year_level})")
        else:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            if old_level is None:
                print(f"  ✓ {filepath.name}: added year_level={year_level}")
            elif old_level != year_level:
                print(f"  ✓ {filepath.name}: updated year_level {old_level} → {year_level}")
            else:
                print(f"  - {filepath.name}: already year_level={year_level}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ {filepath.name}: invalid JSON - {e}")
        return False
    except Exception as e:
        print(f"  ✗ {filepath.name}: error - {e}")
        return False


def patch_from_mapping(mapping_file: Path, dry_run: bool = False) -> int:
    """
    Patch transcripts using a mapping file
    
    Mapping file format (JSON):
    {
        "Desmond_Week5_transcript.json": 8,
        "Coden_Week5_transcript.json": 8,
        "Gabriel_Week5_transcript.json": 7
    }
    
    Or with student names:
    {
        "students": {
            "Desmond": 8,
            "Coden": 8,
            "Gabriel": 7
        },
        "default": 8
    }
    """
    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
    
    patched = 0
    
    if 'students' in mapping:
        # Student name mapping - need to find files
        student_levels = mapping['students']
        default_level = mapping.get('default', 8)
        
        # Find transcript files in current directory and common locations
        search_paths = [
            Path('.'),
            Path('./transcripts'),
            Path('./outputs/transcripts'),
            Path('/mnt/user-data/uploads')
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            for filepath in search_path.glob('*_transcript.json'):
                # Extract student name from filename
                filename = filepath.stem  # e.g., "Desmond_Week5_transcript"
                student_name = filename.split('_')[0]
                
                year_level = student_levels.get(student_name, default_level)
                
                if patch_transcript(filepath, year_level, dry_run):
                    patched += 1
    else:
        # Direct file mapping
        for filename, year_level in mapping.items():
            filepath = Path(filename)
            if not filepath.exists():
                # Try common locations
                for prefix in ['./transcripts/', './outputs/transcripts/', '/mnt/user-data/uploads/']:
                    alt_path = Path(prefix) / filename
                    if alt_path.exists():
                        filepath = alt_path
                        break
            
            if filepath.exists():
                if patch_transcript(filepath, year_level, dry_run):
                    patched += 1
            else:
                print(f"  ✗ {filename}: file not found")
    
    return patched


def main():
    parser = argparse.ArgumentParser(
        description='Patch existing transcript JSON files with year_level field'
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--file', type=str, help='Single transcript file to patch')
    input_group.add_argument('--files', nargs='+', help='Multiple transcript files to patch')
    input_group.add_argument('--dir', type=str, help='Directory containing transcript files')
    input_group.add_argument('--mapping', type=str, help='JSON mapping file with student levels')
    
    # Year level (required unless using mapping)
    parser.add_argument('--year-level', type=int, choices=range(7, 13),
                        help='Year level to set (7-12)')
    
    # Options
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be changed without writing')
    parser.add_argument('--pattern', type=str, default='*_transcript.json',
                        help='File pattern for --dir (default: *_transcript.json)')
    
    args = parser.parse_args()
    
    # Validate year-level requirement
    if not args.mapping and args.year_level is None:
        parser.error("--year-level is required unless using --mapping")
    
    print("Patching transcripts with year_level...")
    if args.dry_run:
        print("(DRY RUN - no files will be modified)\n")
    else:
        print()
    
    patched = 0
    
    if args.mapping:
        mapping_path = Path(args.mapping)
        if not mapping_path.exists():
            print(f"Error: Mapping file not found: {args.mapping}")
            return 1
        patched = patch_from_mapping(mapping_path, args.dry_run)
    
    elif args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"Error: File not found: {args.file}")
            return 1
        if patch_transcript(filepath, args.year_level, args.dry_run):
            patched = 1
    
    elif args.files:
        for filename in args.files:
            filepath = Path(filename)
            if filepath.exists():
                if patch_transcript(filepath, args.year_level, args.dry_run):
                    patched += 1
            else:
                print(f"  ✗ {filename}: file not found")
    
    elif args.dir:
        dirpath = Path(args.dir)
        if not dirpath.exists():
            print(f"Error: Directory not found: {args.dir}")
            return 1
        
        files = list(dirpath.glob(args.pattern))
        if not files:
            print(f"No files matching '{args.pattern}' in {args.dir}")
            return 1
        
        for filepath in sorted(files):
            if patch_transcript(filepath, args.year_level, args.dry_run):
                patched += 1
    
    print(f"\nDone. Patched {patched} file(s).")
    return 0


if __name__ == '__main__':
    exit(main())
