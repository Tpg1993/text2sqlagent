"""
NeMo Guardrails integration for input and output validation.
"""

import os
from typing import Optional, Tuple
from nemoguardrails import RailsConfig, LLMRails
from app.config import settings


class GuardrailManager:
    """
    Manages input and output guardrails using NeMo Guardrails.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize guardrails with configuration.
        
        Args:
            config_path: Path to rails config directory (default: backend/config/rails)
        """
        if config_path is None:
            config_path = os.path.join(settings.BASE_DIR, "config", "rails")
        
        self.rails = None  # Lazy initialized on first use
        try:
            self.config = RailsConfig.from_path(config_path)
            print(f"✅ Guardrails config loaded from {config_path}")
        except Exception as e:
            print(f"⚠️ Failed to load guardrails config: {e}")
            self.config = None

    def _get_rails(self):
        """Lazily initialize LLMRails on first use to avoid blocking startup."""
        if self.rails is None and self.config is not None:
            try:
                self.rails = LLMRails(self.config)
                print("✅ Guardrails LLMRails initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize LLMRails: {e}")
                self.rails = None
        return self.rails

    def validate_input(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user input against guardrails.
        
        Args:
            user_input: The user's query/input
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if input passes guardrails, False otherwise
            - error_message: Explanation if blocked, None if allowed
        """
        if not self._get_rails():
            # Fail-open if guardrails not initialized
            return True, None
        
        try:
            # Check for jailbreak attempts
            response = self._get_rails().generate(
                messages=[{"role": "user", "content": user_input}]
            )
            
            # If NeMo blocks the input, it returns a refusal message
            if response and "cannot" in response.get("content", "").lower():
                return False, "Your request cannot be processed due to safety guidelines."
            
            return True, None
            
        except Exception as e:
            print(f"⚠️ Input validation failed: {e}")
            # Fail-open for availability
            return True, None
    
    def validate_output(self, bot_response: str) -> Tuple[bool, Optional[str]]:
        """
        Validate LLM output against guardrails.
        
        Args:
            bot_response: The LLM's generated response
            
        Returns:
            Tuple of (is_valid, replacement_message)
            - is_valid: True if output passes guardrails, False otherwise
            - replacement_message: Safe message to return if blocked, None if allowed
        """
        if not self._get_rails():
            # Fail-open if guardrails not initialized
            return True, None
        
        try:
            # Use NeMo Guardrails to validate output
            response = self._get_rails().generate(
                messages=[{"role": "bot", "content": bot_response}]
            )
            
            # If NeMo blocks the output, it returns a refusal message
            # We can check if the response content contains a block indicator or refusal
            # Note: The response from rails.generate is usually the *safe* response or the refusal.
            
            if response and "cannot" in response.get("content", "").lower():
                 return False, "I cannot provide that information as it may be harmful or inappropriate."

            return True, None
            
        except Exception as e:
            print(f"⚠️ Output validation failed: {e}")
            # Fail-open for availability
            return True, None


# Global instance for reuse
_guardrail_manager = None

def get_guardrail_manager() -> GuardrailManager:
    """Get or create the global guardrail manager instance."""
    global _guardrail_manager
    if _guardrail_manager is None:
        _guardrail_manager = GuardrailManager()
    return _guardrail_manager
