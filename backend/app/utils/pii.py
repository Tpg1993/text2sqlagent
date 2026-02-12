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
        
        # Define which PII entities to detect
        self.entities_to_detect = [
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "CREDIT_CARD",
            "US_SSN",
            "US_PASSPORT",
            "PERSON",
            "LOCATION",
            "DATE_TIME",
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
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "<{entity_type}>"})
                }
            )
            
            return anonymized_result.text
            
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
