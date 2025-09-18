from abc import ABC, abstractmethod
from typing import Optional
from ..models.models import FileFinding

class BaseDetector(ABC):
    """Base class for all file detectors"""
    
    FILE_NAME_REGEX = r'[-a-zA-Z0-9_.]'
    
    def __init__(self, language: str):
        self.language = language
    

    @abstractmethod
    def match_file(self, filename: str) -> Optional[str]:
        """
        Check if the given filename matches this detector's criteria.
        
        Args:
            filename: The name of the file to check
            
        Returns:
            The file type if matched, None otherwise
        """
        pass

    def create_finding(self, file_path: str, file_type: str) -> FileFinding:
        """
        Create a FileFinding for a matched file.
        
        Args:
            file_path: The path to the matched file
            file_type: The type of file that was matched
            
        Returns:
            A FileFinding instance
        """
        return FileFinding(
            path=file_path,
            language=self.language,
            file_type=file_type
        ) 