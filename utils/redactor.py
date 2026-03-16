import re
from typing import List, Union, Dict, Any, Optional

class Redactor:
    """Utility for redacting PII from text and structured data."""
    
    def __init__(self):
        # Common PII patterns
        self.patterns = {
            "email": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            "phone": r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            "name_indicator": r'(?i)(name|full name|candidate)\s*:\s*([^\n]+)',
            # Note: Complex names usually need NER (LLM based), 
            # but regex handles explicit labels.
        }

    def redact_text(self, text: str, replacement: str = "[REDACTED]") -> str:
        """Redact PII from a string."""
        if not text:
            return text
            
        redacted = text
        for label, pattern in self.patterns.items():
            if label == "name_indicator":
                # For explicit name labels, keep the label but redact the value
                redacted = re.sub(pattern, r'\1: ' + replacement, redacted)
            else:
                redacted = re.sub(pattern, replacement, redacted)
        return redacted

    def redact_json(self, data: Any, replacement: str = "[REDACTED]", 
                    sensitive_keys: Optional[List[str]] = None) -> Any:
        """Recursively redact sensitive keys from a JSON-like object while preserving structure."""
        if sensitive_keys is None:
            sensitive_keys = ["name", "email", "phone", "address", "location", "profiles"]

        if isinstance(data, dict):
            new_dict: Dict[str, Any] = {}
            for k, v in data.items():
                is_sensitive = k.lower() in sensitive_keys
                if is_sensitive:
                    if isinstance(v, (str, bytes, int, float)) or v is None:
                        new_dict[k] = replacement
                    elif isinstance(v, dict):
                        # Redact all values in the dict recursively
                        new_dict[k] = {ik: self.redact_json(iv, replacement, sensitive_keys=["*"]) for ik, iv in v.items()}
                    elif isinstance(v, list):
                        # Redact all items in the list recursively
                        new_dict[k] = [self.redact_json(item, replacement, sensitive_keys=["*"]) for item in v]
                    else:
                        new_dict[k] = replacement
                else:
                    # Special Case: "*" means redact everything at this level and below
                    if sensitive_keys == ["*"]:
                        if isinstance(v, (dict, list)):
                            new_dict[k] = self.redact_json(v, replacement, sensitive_keys=["*"])
                        else:
                            new_dict[k] = replacement
                    else:
                        new_dict[k] = self.redact_json(v, replacement, sensitive_keys)
            return new_dict
        elif isinstance(data, list):
            # Same logic for lists if we are in a "redact all" state
            if sensitive_keys == ["*"]:
                return [self.redact_json(item, replacement, sensitive_keys=["*"]) for item in data]
            return [self.redact_json(item, replacement, sensitive_keys) for item in data]
        else:
            # Leaf node
            if sensitive_keys == ["*"]:
                return replacement
            return data
