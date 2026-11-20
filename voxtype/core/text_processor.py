"""
Text processor for cleaning, formatting, and refining transcribed speech.
"""

import re
from typing import Dict, List, Optional
from voxtype.core.config import TextConfig


# Common Whisper silence / halluncination artifacts
WHISPER_ARTIFACTS = {
    "",
    "you",
    "thank you",
    "thanks for watching",
    "thank you for watching",
    "[blank_audio]",
    "(blank_audio)",
    "[silence]",
    "(silence)",
    "[music]",
    "(music)",
    "[applause]",
    "subtitles by",
}


class TextProcessor:
    """Refines raw speech-to-text transcriptions for natural typing."""

    def __init__(self, config: Optional[TextConfig] = None):
        self.config = config or TextConfig()

    def update_config(self, config: TextConfig) -> None:
        self.config = config

    def clean(self, raw_text: str) -> str:
        """Transforms raw transcription according to active rules."""
        if not raw_text:
            return ""

        text = raw_text.strip()

        # Check for whisper hallucination artifacts on silence
        lowered = text.lower().rstrip("!.,?")
        if lowered in WHISPER_ARTIFACTS:
            return ""

        # Remove filler words if enabled
        if self.config.remove_filler_words and self.config.filler_words:
            text = self._remove_filler_words(text, self.config.filler_words)

        # Smart punctuation and spacing cleanup
        if self.config.auto_punctuate:
            text = self._clean_punctuation_and_spacing(text)

        # Capitalize sentences
        if self.config.auto_capitalize:
            text = self._capitalize_sentences(text)

        # Apply custom text replacements / abbreviations
        if self.config.custom_replacements:
            text = self._apply_replacements(text, self.config.custom_replacements)

        # Add trailing space if configured
        if self.config.add_trailing_space and text and not text.endswith((" ", "\n")):
            text += " "

        return text

    def _remove_filler_words(self, text: str, fillers: List[str]) -> str:
        """Removes standalone filler words like 'um', 'uh', etc."""
        for filler in fillers:
            pattern = rf"\b{re.escape(filler)}\b\s*"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        # Clean up any leftover duplicate spaces or orphaned commas
        text = re.sub(r"\s*,\s*,", ",", text)
        text = re.sub(r"^\s*,\s*", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _apply_replacements(self, text: str, replacements: Dict[str, str]) -> str:
        """Applies user-defined phrase replacements (e.g. 'new line' -> '\n')."""
        for trigger, replacement in replacements.items():
            pattern = rf"\b{re.escape(trigger)}\b"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _clean_punctuation_and_spacing(self, text: str) -> str:
        """Normalizes spaces around punctuation marks."""
        # Remove space before punctuation: "hello , world" -> "hello, world"
        text = re.sub(r"\s+([,.:;?!])", r"\1", text)
        # Ensure single space after punctuation if followed by word character
        text = re.sub(r"([,.:;?!])([^\s0-9])", r"\1 \2", text)
        # Collapse multiple spaces
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _capitalize_sentences(self, text: str) -> str:
        """Capitalizes the first character and characters following sentence-terminating punctuation."""
        if not text:
            return ""

        # Capitalize very first letter
        result = list(text)
        # Find first non-whitespace
        for i, ch in enumerate(result):
            if ch.isalpha():
                result[i] = ch.upper()
                break

        reconstructed = "".join(result)

        # Capitalize after . ! ? followed by whitespace
        def capitalize_match(match: re.Match) -> str:
            return match.group(1) + match.group(2).upper()

        reconstructed = re.sub(r"([.!?]\s+)([a-z])", capitalize_match, reconstructed)
        return reconstructed
