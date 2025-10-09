from typing import List
import os
from .base import BaseExecutor
from ..models.models import FileFinding, PackageFinding, ScanType
from ..utils.package_checker import check_packages_async
from .package_parsers import UvParser

class UvLockExecutor(BaseExecutor):
    """Executor for checking Python uv.lock files"""
    
    supported_language = "python"
    supported_file_types = ["uvlock"]
    
    def __init__(self, project_root):
        super().__init__(project_root)

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        """Check if this is a Python uv.lock file"""
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Scan uv.lock file for dependencies asynchronously
        
        Args:
            file_finding (FileFinding): Information about the file to scan
            
        Returns:
            List[PackageFinding]: Results of the scan
        """
        findings = []
        
        content = self._read_file(file_finding)
        lines = content.split('\n')
    
        # Use the new UvParser instead of internal parsing method
        packages = UvParser.parse_uvlock_file(content)
        
        # Check all packages asynchronously
        package_exists_results = await check_packages_async(packages, "pypi")
        
        # Process results
        for package, exists in zip(packages, package_exists_results):
            if not exists:
                # Find line number where package is mentioned
                line_number = 1  # Default if we can't find it
                for i, line in enumerate(lines):
                    if f'name = "{package}"' in line or f"name = '{package}'" in line:
                        line_number = i + 1  # Convert to 1-based line number
                        break
                
                findings.append(PackageFinding(
                    name=package,
                    file_path=file_finding.path,
                    scan_type=ScanType.PYTHON_UVLOCK,
                    language=self.supported_language,
                    start_line=line_number,
                    end_line=line_number,
                    code_snippet=f"Package '{package}' is unclaimed and publicly available for anyone to register."
                ))
                    
        return findings
