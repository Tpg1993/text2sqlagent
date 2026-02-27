"""
PII Detection and Anonymization using Microsoft Presidio.
This module scrubs sensitive information before data is stored in the vector database.
"""

from typing import List
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


class PIIScrubber:
    """
    Detects and anonymizes PII using Microsoft Presidio.
    """
    
    def __init__(self):
        """Initialize Presidio analyzer and anonymizer engines."""
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Add a custom recognizer for alphanumeric phone numbers like "1-800-AGENTIC"
        from presidio_analyzer import Pattern, PatternRecognizer
        
        # Matches patterns like 1-800-COMPANY or 800-COMPANY
        alphanumeric_phone_pattern = Pattern(
            name="alphanumeric_phone",
            regex=r"\b1-[0-9]{3}-[A-Z0-9]{4,10}\b|\b[0-9]{3}-[A-Z0-9]{4,10}\b",
            score=0.8
        )
        custom_phone_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            name="alphanumeric_phone_recognizer",
            patterns=[alphanumeric_phone_pattern]
        )
        self.analyzer.registry.add_recognizer(custom_phone_recognizer)
        
        # Define which PII entities to detect
        self.entities_to_detect = [
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "CREDIT_CARD",
            "US_SSN",
            "US_PASSPORT",
            "PERSON",
            "LOCATION",
            "IBAN_CODE",
            "IP_ADDRESS",
            "URL",
        ]
    
    def scrub_text(self, text: str, language: str = "en") -> str:
        """
        Detect and anonymize PII in the given text.
        
        Args:
            text: Input text to scrub
            language: Language code (default: "en")
            
        Returns:
            Text with PII replaced by placeholders (e.g., <EMAIL_ADDRESS>)
        """
        if not text or not text.strip():
            return text
        
        try:
            # Analyze text for PII
            results = self.analyzer.analyze(
                text=text,
                entities=self.entities_to_detect,
                language=language
            )
            
            # Anonymize detected PII
            
            # Create a dictionary of operators for each detected entity type
            # We map each to a custom replacement function that uses the vault
            from app.db.vault import store_pii
            
            # Post-processing: replacing entities manually using the vault
            # Presidio's AnonymizerEngine makes it difficult to pass dynamic lambdas that need the original text 
            # easily, so we will do the replacement ourselves using the analyzer results.
            
            # Filter out overlapping entities (e.g. EMAIL_ADDRESS and URL overlapping for the same text)
            # We sort by start position ascending, and prioritize larger spans/higher scores greedy approach
            sorted_by_start = sorted(results, key=lambda x: (x.start, -(x.end - x.start), -x.score))
            filtered_results = []
            last_end = -1
            for r in sorted_by_start:
                if r.start >= last_end:
                    filtered_results.append(r)
                    last_end = r.end
            
            # Sort results in reverse order so replacing text doesn't mess up earlier indices
            sorted_results = sorted(filtered_results, key=lambda x: x.start, reverse=True)
            
            scrubbed_text = text
            for result in sorted_results:
                original_value = text[result.start:result.end]
                token = store_pii(result.entity_type, original_value)
                
                # Replace the original value with the token
                scrubbed_text = scrubbed_text[:result.start] + token + scrubbed_text[result.end:]
                
            return scrubbed_text
            
        except Exception as e:
            print(f"⚠️ PII scrubbing failed: {e}")
            # Return original text if scrubbing fails (fail-open for availability)
            return text
    
    def detect_pii(self, text: str, language: str = "en") -> List[dict]:
        """
        Detect PII without anonymizing (for logging/monitoring).
        
        Args:
            text: Input text to analyze
            language: Language code (default: "en")
            
        Returns:
            List of detected PII entities with metadata
        """
        try:
            results = self.analyzer.analyze(
                text=text,
                entities=self.entities_to_detect,
                language=language
            )
            
            return [
                {
                    "entity_type": result.entity_type,
                    "start": result.start,
                    "end": result.end,
                    "score": result.score,
                    "text": text[result.start:result.end]
                }
                for result in results
            ]
            
        except Exception as e:
            print(f"⚠️ PII detection failed: {e}")
            return []


# Global instance for reuse
_pii_scrubber = None

def get_pii_scrubber() -> PIIScrubber:
    """Get or create the global PII scrubber instance."""
    global _pii_scrubber
    if _pii_scrubber is None:
        _pii_scrubber = PIIScrubber()
    return _pii_scrubber
