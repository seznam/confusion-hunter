import json
import os
from typing import Dict, List, Optional, Pattern
import re
from .base import BaseDetector


class SchemaBasedDetector(BaseDetector):
    """A detector that is configured from a JSON schema"""
    
    def __init__(self, language: str, file_types: Dict[str, Dict[str, List[str]]]):
        """
        Initialize a schema-based detector.
        
        Args:
            language: The programming language this detector handles
            file_types: Dictionary mapping file types to their allow/deny patterns
        """
        super().__init__(language)
        self.file_types = file_types
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, Dict[str, List[Pattern]]]:
        """Compile regex patterns for efficient matching"""
        compiled = {}
        
        for file_type, rules in self.file_types.items():
            compiled[file_type] = {
                'allow': [re.compile(pattern) for pattern in rules.get('allow', [])],
                'deny': [re.compile(pattern) for pattern in rules.get('deny', [])]
            }
        
        return compiled
    
    def match_file(self, filename: str) -> Optional[str]:
        """Check if the filename matches any patterns in the schema"""
        for file_type, patterns in self._compiled_patterns.items():
            # Check if filename matches any allow patterns
            matches_allow = any(pattern.match(filename) for pattern in patterns['allow'])
            
            if matches_allow:
                # Check if filename matches any deny patterns
                matches_deny = any(pattern.match(filename) for pattern in patterns['deny'])
                
                if not matches_deny:
                    return file_type
        
        return None


class SchemaLoader:
    """Loads detector schemas from JSON files"""
    
    @staticmethod
    def load_schema(schema_path: str) -> Dict:
        """Load a schema from a JSON file"""
        with open(schema_path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def create_detector(schema_path: str) -> SchemaBasedDetector:
        """Create a detector instance from a schema file"""
        schema = SchemaLoader.load_schema(schema_path)
        return SchemaBasedDetector(
            language=schema['language'],
            file_types=schema['file_types']
        )
    
    @staticmethod
    def create_detector_from_dict(schema: Dict) -> SchemaBasedDetector:
        """Create a detector instance from a schema dictionary"""
        return SchemaBasedDetector(
            language=schema['language'],
            file_types=schema['file_types']
        )


def load_detectors_from_schemas(schemas_dir: str) -> Dict[str, SchemaBasedDetector]:
    """Load all detectors from schema files in a directory"""
    detectors = {}
    
    if not os.path.exists(schemas_dir):
        return detectors
    
    for filename in os.listdir(schemas_dir):
        if filename.endswith('.json'):
            schema_path = os.path.join(schemas_dir, filename)
            detector_name = filename[:-5]  # Remove .json extension
            detectors[detector_name] = SchemaLoader.create_detector(schema_path)
    
    return detectors
