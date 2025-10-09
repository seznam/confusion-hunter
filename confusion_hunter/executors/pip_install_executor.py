from typing import List
from .base import BaseExecutor
from .package_parsers.pip_parser import PIPParser
from ..utils.package_checker import check_packages_async
from ..models.models import FileFinding, PackageFinding, ScanType

class PIPInstallExecutor(BaseExecutor):

    supported_language = "python"
    supported_file_types = ["dockerfile", "gitlab-ci", "script"]

    pip_parser = PIPParser()
    
    def should_scan_file(self, file_finding: FileFinding) -> bool:
        return file_finding.language == self.supported_language and file_finding.file_type in self.supported_file_types

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        content = self._read_file(file_finding)

        installs = self.pip_parser.get_packages(content, file_finding.file_type)
        findings = []
        
        # Collect all packages to check
        all_packages = []
        package_to_install_map = {}  # Map packages to their install info
        
        for install in installs:
            for package in install.packages:
                all_packages.append(package)
                package_to_install_map[package] = install

        # Check all packages asynchronously
        package_exists_results = await check_packages_async(all_packages, "pypi")
        
        # Process results
        for package, exists in zip(all_packages, package_exists_results):
            if not exists:
                install = package_to_install_map[package]
                findings.append(PackageFinding(
                    name=package,
                    file_path=file_finding.path,
                    scan_type=ScanType.PYTHON_PIP,
                    language=self.supported_language,
                    start_line=install.line_numbers[0],
                    end_line=install.line_numbers[1],
                    code_snippet=install.snippet
                ))
                
        return findings

