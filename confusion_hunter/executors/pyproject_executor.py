from typing import List
import os
import re
from .base import BaseExecutor
from ..models.models import FileFinding, PackageFinding, ScanType
from ..utils.package_checker import check_packages_async
from .package_parsers.pyproject_parser import PyprojectParser

class PyprojectExecutor(BaseExecutor):
    """Executor for checking Python pyproject.toml files"""
    
    supported_language = "python"
    supported_file_types = ["pyproject"]
    
    def __init__(self, project_root):
        super().__init__(project_root)

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        """Check if this is a Python pyproject.toml file"""
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Scan pyproject.toml file for dependencies asynchronously
        
        Args:
            file_finding (FileFinding): Information about the file to scan
            
        Returns:
            List[PackageFinding]: Results of the scan
        """
        findings = []
        
        try:
            # Use _read_file from BaseExecutor for consistency
            content = self._read_file(file_finding)
            lines = content.split('\n')
            
            # Use the PyprojectParser to extract package names
            packages = PyprojectParser.get_packages(os.path.join(self.project_root, file_finding.path))
            
            # Check if there are any packages to check
            if not packages:
                return findings
            
            # Check all packages asynchronously in one batch
            package_exists_results = await check_packages_async(packages, "pypi")
            
            # Process results
            for package, exists in zip(packages, package_exists_results):
                if not exists:
                    # Find line number where package is mentioned
                    line_number = 1  # Default if we can't find it
                    code_snippet = None
                    
                    for i, line in enumerate(lines):
                        # More precise patterns for different dependency formats in pyproject.toml
                        if (f'"{package}"' in line or 
                            f"'{package}'" in line or 
                            f"{package} =" in line or 
                            f"{package}," in line or
                            line.strip() == package or
                            re.search(rf'["\']{package}["\']', line)):
                            line_number = i + 1  # Convert to 1-based line number
                            code_snippet = lines[i].strip()
                            break
                    
                    findings.append(PackageFinding(
                        name=package,
                        file_path=file_finding.path,
                        scan_type=ScanType.PYTHON_PYPROJECT,
                        language=self.supported_language,
                        start_line=line_number,
                        end_line=line_number,
                        code_snippet=code_snippet if code_snippet else f"Package '{package}' is unclaimed and publicly available for anyone to register."
                    ))
                    
        except Exception as e:
            print(f"Error scanning {file_finding.path}: {type(e).__name__}: {str(e)}")
            
        return findings
