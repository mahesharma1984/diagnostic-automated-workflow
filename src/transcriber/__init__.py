"""
Transcriber Package

Handles image → text transcription with confidence scoring.
"""

from .core import TVODETranscriber, TranscriptionResult, Uncertainty

__all__ = ['TVODETranscriber', 'TranscriptionResult', 'Uncertainty']
