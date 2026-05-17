"""Personalization utility for marketing messages."""

from src.services.marketing.base import PersonalizerInterface

class SimplePersonalizer(PersonalizerInterface):
    """Basic string replacement personalizer."""

    def personalize(self, template: str, context: dict) -> str:
        """Replace {key} placeholders with values from context."""
        text = template
        # Standardize keys to common variations
        mapping = {
            "{name}": context.get("first_name", ""),
            "{first_name}": context.get("first_name", ""),
            "{last_name}": context.get("last_name", ""),
            "{company}": context.get("company", ""),
            "{position}": context.get("position", ""),
        }
        
        for placeholder, value in mapping.items():
            text = text.replace(placeholder, str(value or ""))
            
        return text
