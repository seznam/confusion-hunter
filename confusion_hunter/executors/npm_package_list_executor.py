from typing import List
from .base import BaseExecutor
from ..utils.package_checker import check_packages_async
from ..models.models import FileFinding, PackageFinding, ScanType


class NPMPackageListExecutor(BaseExecutor):
    """Executor for handling npm package lists"""

    supported_language = "javascript"
    supported_file_types = ["package-list"]

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    def _read_package_list(self, file_finding: FileFinding) -> List[str]:
        """Read package list from the file finding"""
        # For package-list type, the path contains the actual package names
        return file_finding.path.split(',') if file_finding.path else []

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """Scan npm packages for unclaimed status"""
        packages = self._read_package_list(file_finding)
        
        if not packages:
            return []

        # Check packages asynchronously (npm packages are case-sensitive, no normalization)
        package_exists_results = await check_packages_async(packages, "npm")
        
        # Create findings for unclaimed packages
        findings = []
        for i, (package, exists) in enumerate(zip(packages, package_exists_results)):
            if not exists:
                finding = PackageFinding(
                    name=package,
                    file_path=file_finding.path,
                    scan_type=ScanType.JS_PACKAGE_LIST,
                    language=self.supported_language,
                    severity="warning",
                    message=f"Package '{package}' is unclaimed in NPM registry and publicly available for anyone to register.",
                    start_line=i + 1,
                    end_line=i + 1
                )
                findings.append(finding)
        
        return findings
