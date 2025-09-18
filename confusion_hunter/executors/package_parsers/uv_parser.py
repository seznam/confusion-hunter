import re
from typing import List

# Precompile regex patterns for better performance
PACKAGE_SECTION_PATTERN = re.compile(r'\[\[package\]\](.*?)(?=\[\[package\]\]|\Z)', re.DOTALL)
NAME_PATTERN = re.compile(r'name\s*=\s*["\']([^"\']+)["\']')
SOURCE_PATTERN = re.compile(r'source\s*=\s*\{([^}]+)\}')

class UvParser:
    """Parser for UV lock files"""
    
    @staticmethod
    def get_packages(file_path: str) -> List[str]:
        """
        Parse uv.lock file and extract package dependencies.
        Standard method name for consistent interface across parsers.
        
        Args:
            file_path (str): Path to the uv.lock file
            
        Returns:
            List[str]: List of package names
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return UvParser.parse_uvlock_file(content)
        except Exception as e:
            print(f"Error reading uv.lock file at {file_path}: {str(e)}")
            return []
    
    @staticmethod
    def parse_uvlock_file(content: str) -> List[str]:
        """Parse uv.lock file and extract package names"""
        packages = []

        # uv.lock is TOML-like but might not be standard TOML
        # We'll parse it manually to be safe
        
        # Extract package sections
        package_sections = PACKAGE_SECTION_PATTERN.findall(content)
        
        for section in package_sections:
            # Extract package name
            name_match = NAME_PATTERN.search(section)
            if not name_match:
                continue
                
            package_name = name_match.group(1)
            
            # Filter out packages with invalid characters (only allow a-z, A-Z, 0-9, -, _)
            if not re.match(r'^[a-zA-Z0-9_-]+$', package_name):
                continue
            
            # Check if this is a local/virtual package that should be skipped
            if UvParser._is_local_package(section):
                continue
                
            # Add packages from external registries only
            packages.append(package_name)
            
        return packages

    @staticmethod
    def _is_local_package(section: str) -> bool:
        """
        Check if a package section represents a local/virtual package.
        Returns True for packages that are not from external registries.
        
        This uses a dynamic approach by analyzing the actual values in the source
        specification rather than looking for specific keywords.
        
        Args:
            section (str): The package section content from uv.lock
            
        Returns:
            bool: True if this is a local package, False if it's from an external source
        """
        # Extract source field
        source_match = SOURCE_PATTERN.search(section)
        if not source_match:
            # No source field means it's likely from a registry
            return False
            
        source_content = source_match.group(1).strip()
        
        # Extract all quoted values from the source specification
        # This captures values like ".", "/path", "https://...", etc.
        quoted_values = re.findall(r'["\']([^"\']*)["\']', source_content)
        
        for value in quoted_values:
            # Check if this value looks like an external URL/registry
            if UvParser._is_external_source(value):
                return False  # This is an external package
                
        # If we get here, either:
        # 1. No quoted values were found (likely virtual/built-in)
        # 2. All quoted values look like local paths
        # In both cases, consider it local
        return True
    
    @staticmethod
    def _is_external_source(value: str) -> bool:
        """
        Check if a source value represents an external source that should be checked
        for dependency confusion attacks.
        
        Private repositories and internal packages should be checked because an attacker
        could register the same package name on PyPI. Public repositories from well-known
        hosts are less likely to be vulnerable.
        
        Args:
            value (str): A value from the source specification
            
        Returns:
            bool: True if this looks like an external source that could be vulnerable
        """
        if not value:
            return False
            
        # Check for URLs
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', value):
            # Public GitHub repositories in path are not dependency confusion targets
            if 'github.com' in value.lower() or 'gitlab.com' in value.lower():
                return False
            # Other URLs (private GitLab, Bitbucket, etc.) should be checked
            return True
            
        # Check for Git SSH URLs (git@host:repo format)
        if re.match(r'^[^@]+@[^:]+:', value):
            # SSH URLs typically indicate private repositories that should be checked
            return True
            
        # If none of the above patterns match, it might be a local path
        # Local paths should not be checked
        return False