from typing import List
import os
import re
from .base import BaseExecutor
from ..models.models import FileFinding, PackageFinding, ScanType
from ..utils.package_checker import check_packages_async
from .package_parsers.pipfile_parser import PipfileParser

class PipfileExecutor(BaseExecutor):
    """Executor for checking Python Pipfile files"""
    
    supported_language = "python"
    supported_file_types = ["pipfile"]
    
    def __init__(self, project_root):
        super().__init__(project_root)

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        """Check if this is a Python Pipfile"""
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Scan Pipfile for dependencies asynchronously
        
        Args:
            file_finding (FileFinding): Information about the file to scan
            
        Returns:
            List[PackageFinding]: Results of the scan
        """
        findings = []
        
        try:
            content = self._read_file(file_finding)
            lines = content.split('\n')
            
            file_path = os.path.join(self.project_root, file_finding.path)
            packages = PipfileParser.get_packages(file_path)
            
            if not packages:
                return findings
            
            package_exists_results = await check_packages_async(packages, "pypi")
            
            for package, exists in zip(packages, package_exists_results):
                if not exists:
                    line_number = 1  # Default if we can't find it
                    code_snippet = None
                    
                    for i, line in enumerate(lines):
                        # Skip comment lines when searching for package declarations
                        if line.strip().startswith('#'):
                            continue
                            
                        if (f'"{package}"' in line or 
                            f"'{package}'" in line or 
                            f"{package} =" in line or
                            f"{package}=" in line or
                            re.search(rf'[\s=]["\']*{re.escape(package)}["\']*', line)):
                            line_number = i + 1  # Convert to 1-based line number
                            code_snippet = line.strip()
                            break
                    
                    findings.append(PackageFinding(
                        name=package,
                        file_path=file_finding.path,
                        scan_type=ScanType.PYTHON_PIPFILE,
                        language=self.supported_language,
                        start_line=line_number,
                        end_line=line_number,
                        code_snippet=code_snippet or f"Package '{package}' is unclaimed and publicly available for anyone to register."
                    ))
                
        except Exception as e:
            pass
            
        return findings