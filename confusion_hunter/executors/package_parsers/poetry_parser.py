import re
from typing import List

# Precompile regex patterns for better performance
PACKAGE_SECTION_PATTERN = re.compile(r'\[\[package\]\](.*?)(?=\[\[package\]\]|\[metadata\]|\Z)', re.DOTALL)
NAME_PATTERN = re.compile(r'name\s*=\s*["\']([^"\']+)["\']')
DEPENDENCIES_SECTION_PATTERN = re.compile(r'\[package\.dependencies\](.*?)(?=\[package\.|\Z)', re.DOTALL)
# More specific pattern: must be at start of line, followed by space and =, and not inside quotes or markers
DEPENDENCIES_PATTERN = re.compile(r'^([a-zA-Z0-9_][a-zA-Z0-9_.-]*)\s*=\s*(?:["\']|{)', re.MULTILINE)
EXTRAS_SECTION_PATTERN = re.compile(r'\[package\.extras\](.*?)(?=\[package\.|\Z)', re.DOTALL)
# More specific pattern: avoid matching logical operators like 'and', 'or' in environment markers
EXTRAS_WITH_VERSION_PATTERN = re.compile(r'["\']\s*([a-zA-Z0-9_][a-zA-Z0-9_.-]*[a-zA-Z0-9_])\s*\((?:[><=!]|==)')
EXTRAS_WITHOUT_VERSION_PATTERN = re.compile(r'["\']\s*([a-zA-Z0-9_][a-zA-Z0-9_.-]+)\s*["\']')
# More specific pattern for optional packages - must have {version = pattern
OPTIONAL_PKGS_PATTERN = re.compile(r'^([a-zA-Z0-9_][a-zA-Z0-9_.-]+)\s*=\s*\{version\s*=', re.MULTILINE)
VERSION_NUMBER_PATTERN = re.compile(r'^\d+(\.\d+)*$')

class PoetryParser:
    """Parser for Poetry lock files"""
    
    @staticmethod
    def get_packages(file_path: str) -> List[str]:
        """
        Parse poetry.lock file and extract package dependencies.
        Standard method name for consistent interface across parsers.
        
        Args:
            file_path (str): Path to the poetry.lock file
            
        Returns:
            List[str]: List of package names
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return PoetryParser.parse_poetry_lock_file(content)
        except Exception as e:
            print(f"Error reading poetry.lock file at {file_path}: {str(e)}")
            return []
    
    @staticmethod
    def parse_poetry_lock_file(content: str) -> List[str]:
        """
        Parse poetry.lock file and extract all package names, including dependencies and extras.
        Returns a list of unique package names, filtering out version numbers.
        """
        unique_packages = set()

        # Extract package sections using regex
        package_sections = PACKAGE_SECTION_PATTERN.findall(content)
        
        for section in package_sections:
            # Extract main package name
            name_match = NAME_PATTERN.search(section)
            if name_match:
                package_name = name_match.group(1)
                
                # Skip local/development packages
                if not PoetryParser._is_local_package(section):
                    unique_packages.add(package_name)
            
            # Extract dependencies from package.dependencies section
            dependencies_match = DEPENDENCIES_SECTION_PATTERN.search(section)
            if dependencies_match:
                deps_section = dependencies_match.group(1).strip()
                # Match package names at the start of lines, excluding version numbers
                dep_matches = DEPENDENCIES_PATTERN.findall(deps_section)
                for dep in dep_matches:
                    if not VERSION_NUMBER_PATTERN.match(dep):  # Skip if it's just a version number
                        unique_packages.add(dep)
            
            # Extract extras section package names
            extras_match = EXTRAS_SECTION_PATTERN.search(section)
            if extras_match:
                extras_section = extras_match.group(1).strip()
                
                # Get group names to exclude them
                group_names = set(DEPENDENCIES_PATTERN.findall(extras_section))
                
                # Format: all = ["flake8 (>=7.1.1)", "mypy (>=1.11.2)", "pytest (>=8.3.2)", "ruff (>=0.6.2)"]
                extras_pkgs = EXTRAS_WITH_VERSION_PATTERN.findall(extras_section)
                for pkg in extras_pkgs:
                    if not VERSION_NUMBER_PATTERN.match(pkg) and pkg not in group_names:
                        unique_packages.add(pkg)
                
                # Format: urllib3-fastrpc = ["example-urllib3-client"]
                # This captures packages in extras that don't have version constraints in parentheses
                extras_pkgs_without_version = EXTRAS_WITHOUT_VERSION_PATTERN.findall(extras_section)
                for pkg in extras_pkgs_without_version:
                    if not VERSION_NUMBER_PATTERN.match(pkg) and pkg not in group_names:
                        unique_packages.add(pkg)
        
        # Look for optional packages with version markers - packages referenced in a more complex way
        optional_pkgs_matches = OPTIONAL_PKGS_PATTERN.findall(content)
        for pkg in optional_pkgs_matches:
            if not VERSION_NUMBER_PATTERN.match(pkg):  # Skip if it's just a version number
                unique_packages.add(pkg)
            
        return list(unique_packages)
    
    @staticmethod
    def _is_local_package(section: str) -> bool:
        """
        Check if a package section represents a local/development package.
        Returns True for packages that are not from PyPI.
        
        Args:
            section (str): The package section content from poetry.lock
            
        Returns:
            bool: True if this is a local package, False if it's from PyPI
        """
        # Check for development packages
        if re.search(r'develop\s*=\s*true', section, re.IGNORECASE):
            return True
            
        # Check for Git sources
        if re.search(r'source\s*=\s*["\']git["\']', section):
            return True
            
        # Check for Git URLs in source.url
        git_url_match = re.search(r'url\s*=\s*["\']([^"\']+)["\']', section)
        if git_url_match:
            url = git_url_match.group(1)
            # If it's a Git URL, it's not from PyPI
            if (url.startswith(('git+', 'git://')) or 
                'github.com' in url or 'gitlab.com' in url or 
                url.endswith('.git')):
                return True
        
        # Check for local file sources
        if re.search(r'source\s*=\s*["\']file["\']', section):
            return True
            
        # Check for local paths in source.url
        path_url_match = re.search(r'url\s*=\s*["\']([^"\']+)["\']', section)
        if path_url_match:
            url = path_url_match.group(1)
            # Local file paths
            if url.startswith(('file://', './', '../', '/')):
                return True
        
        # If none of the above, assume it's from PyPI
        return False