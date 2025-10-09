from typing import List
import os
import re
from .base import BaseExecutor
from ..models.models import FileFinding, PackageFinding, ScanType
from ..utils.package_checker import check_packages_async
from .package_parsers.base import DetectedCommand

class RequirementsExecutor(BaseExecutor):
    """Executor for checking Python requirements.txt files"""
    
    supported_language = "python"
    supported_file_types = ["requirements"]
    
    def __init__(self, project_root):
        super().__init__(project_root)

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        """Check if this is a Python requirements.txt file"""
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    def _parse_requirements_file(self, content: str) -> List[DetectedCommand]:
        """Parse requirements.txt file and extract package names"""
        packages = []
        lines = content.split('\n')

        for line_index, line in enumerate(lines):
            # Remove comments
            line = re.sub(r'#.*$', '', line).strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip options and URLs
            if line.startswith('-') or line.startswith('--') or line.startswith('http'):
                continue
            
            # Skip local file dependencies (various formats)
            if self._is_local_dependency(line):
                continue
            
            # Handle direct URL installations with #egg=
            if '#egg=' in line:
                egg_part = line.split('#egg=')[1].strip()
                package = egg_part.split('&')[0].strip()  # Handle additional URL params
                packages.append(DetectedCommand(packages=[package], line_numbers=(line_index + 1, line_index + 1), snippet=line))
                continue
            
            # Extract package name handling all Python version specifiers and edge cases
            package = self._extract_package_name_from_requirement(line)
            
            # Basic validation for package names - more permissive to allow hyphens, underscores, dots
            if (package and 
                re.match(r'^[a-zA-Z0-9][-_.a-zA-Z0-9]*$', package)):
                packages.append(DetectedCommand(packages=[package], line_numbers=(line_index + 1, line_index + 1), snippet=line))
            
        return packages

    def _is_local_dependency(self, line: str) -> bool:
        """
        Check if a requirements line represents a local dependency.
        Returns True for local file paths, Git repositories, etc.
        
        Args:
            line (str): A line from requirements.txt
            
        Returns:
            bool: True if this is a local dependency, False otherwise
        """
        line = line.strip()
        
        # PEP 440 direct references using @ syntax
        if ' @ ' in line:
            # Split on @ to get the URL/path part
            _, url_part = line.split(' @ ', 1)
            url_part = url_part.strip()
            
            # Check for local file URLs
            if url_part.startswith(('file://', 'file:')):
                return True
                
            # Check for Git repositories (not from PyPI)
            if any(protocol in url_part for protocol in ['git+', 'git://', 'git+ssh://', 'git+https://', 'ssh://']):
                return True
                
            # Check for direct HTTP/HTTPS URLs (not PyPI)
            if url_part.startswith(('http://', 'https://')) and 'pypi.org' not in url_part:
                return True
        
        # Direct local paths
        if line.startswith(('./', '../', '/')):
            return True
            
        # Relative paths without ./ prefix
        if '/' in line and not line.startswith('http') and '@' not in line:
            # This might be a local path, but be careful not to filter scoped packages
            # Only consider it local if it looks like a path (contains path separators)
            return True
            
        return False

    def _extract_package_name_from_requirement(self, requirement_line: str) -> str:
        """
        Extract package name from a requirement string, ignoring version specifiers.
        This method is kept for backward compatibility.
        
        Args:
            requirement_line (str): A requirement line from requirements.txt
            
        Returns:
            str: The package name
        """
        # Remove comments
        line = re.sub(r'#.*$', '', requirement_line).strip()
        
        # Handle direct URL installations with #egg=
        if '#egg=' in line:
            egg_part = line.split('#egg=')[1].strip()
            return egg_part.split('&')[0].strip()  # Handle additional URL params
        
        # Extract package name (remove version specifiers, etc.)
        # Handle various version specifiers: ==, >=, <=, >, <, ~=, !=, ===
        package = re.split(r'[=<>!~]+=?', line)[0].strip()
        
        # Remove any trailing extras or options
        if '[' in package:
            package = package.split('[')[0]
        
        # Remove trailing semicolons and environment markers
        if ';' in package:
            package = package.split(';')[0].strip()
            
        return package

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Scan requirements.txt file for dependencies asynchronously
        
        Args:
            file_finding (FileFinding): Information about the file to scan
            
        Returns:
            List[PackageFinding]: Results of the scan
        """
        findings = []
        
        content = self._read_file(file_finding)
            
        packages = self._parse_requirements_file(content)
        
        # Process results
        for package in packages:
            package_exists_results = await check_packages_async(package.packages, "pypi")

            for package_name, exists in zip(package.packages, package_exists_results):
                if not exists:
                    findings.append(PackageFinding(
                        name=package_name,
                        file_path=file_finding.path,
                        scan_type=ScanType.PYTHON_REQUIREMENTS,
                        language="python",
                        start_line=package.line_numbers[0],
                        end_line=package.line_numbers[1],
                        code_snippet=package.snippet
                    ))

        return findings