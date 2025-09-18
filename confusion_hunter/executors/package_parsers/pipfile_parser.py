import re
import sys
from typing import List, Dict, Any, Set

# Precompile regex patterns for better performance
PACKAGE_SECTION_PATTERN = re.compile(r'\[packages\](.*?)(?=\[|\Z)', re.DOTALL)
DEV_PACKAGE_SECTION_PATTERN = re.compile(r'\[dev-packages\](.*?)(?=\[|\Z)', re.DOTALL)
SIMPLE_PACKAGE_PATTERN = re.compile(r'([a-zA-Z0-9_.-]+)\s*=\s*(?:["\']([^"\']+)["\']|[\s"\']*\*[\s"\']*)')
COMPLEX_PACKAGE_PATTERN = re.compile(r'([a-zA-Z0-9_.-]+)\s*=\s*\{')

class PipfileParser:
    """Parser for Pipfile files used by pipenv"""
    
    @staticmethod
    def _clean_package_name(package_name: str) -> str:
        """
        Clean a package name by removing extras in square brackets.
        For example, "fastapi[standard]" becomes "fastapi".
        
        Args:
            package_name (str): Raw package name possibly with extras
                
        Returns:
            str: Clean package name without extras, or empty string if invalid
        """
        # Strip out any [extras] from the package name
        if "[" in package_name:
            package_name = package_name.split("[")[0]
        
        # Filter out packages with invalid characters (only allow a-z, A-Z, 0-9, -, _)
        if not re.match(r'^[a-zA-Z0-9_-]+$', package_name):
            return ""
            
        return package_name

    @staticmethod
    def get_packages(file_path: str) -> List[str]:
        """
        Parse Pipfile and extract all package names (both regular and dev packages).
        Returns a list of unique package names.
        
        This is the standard method name used across all parsers.
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            packages = set()
            
            # Process both package sections with the same function
            PipfileParser._extract_packages_from_sections(
                PACKAGE_SECTION_PATTERN.findall(content), packages)
            PipfileParser._extract_packages_from_sections(
                DEV_PACKAGE_SECTION_PATTERN.findall(content), packages)
            
            # Clean package names and remove duplicates
            result = list(set(PipfileParser._clean_package_name(pkg) for pkg in packages))
            return result
            
        except Exception as e:
            return []
    
    @staticmethod
    def _extract_packages_from_sections(sections: List[str], packages: Set[str]) -> None:
        """
        Extract package names from section content and add them to the packages set.
        
        Args:
            sections: List of section content strings
            packages: Set to add package names to
        """
        for section in sections:
            # Process each line in the section
            for line in section.strip().split('\n'):
                # Skip comments and empty lines
                if not line.strip() or line.strip().startswith('#'):
                    continue
                
                # Simple format: package = "version" or package = '*'
                simple_match = SIMPLE_PACKAGE_PATTERN.match(line)
                if simple_match:
                    package_name = simple_match.group(1)
                    cleaned_name = PipfileParser._clean_package_name(package_name)
                    if cleaned_name:  # Only add if valid package name
                        packages.add(cleaned_name)
                    continue
                        
                # Complex format: package = { version = "x", index = "y" }
                complex_match = COMPLEX_PACKAGE_PATTERN.match(line)
                if complex_match:
                    package_name = complex_match.group(1)
                    
                    # Check if this is a local package (has 'path' specification)
                    # Local packages should be skipped as they're not from PyPI
                    if 'path' in line:
                        continue  # Skip local packages
                    
                    cleaned_name = PipfileParser._clean_package_name(package_name)
                    if cleaned_name:  # Only add if valid package name
                        packages.add(cleaned_name)
                    continue
    
    # Kept for backward compatibility
    @staticmethod
    def get_all_packages(file_path: str) -> List[str]:
        """Alias for get_packages for backward compatibility"""
        return PipfileParser.get_packages(file_path)