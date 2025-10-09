from typing import List, Dict, Any
from .base import BaseExecutor
from ..utils.package_checker import check_packages_async
from ..models.models import FileFinding, PackageFinding, ScanType


class MavenPackageListExecutor(BaseExecutor):
    """Executor for handling maven package lists"""

    supported_language = "java"
    supported_file_types = ["package-list"]

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    def _parse_maven_package(self, package_str: str) -> Dict[str, str]:
        """Parse Maven package string in format groupId:artifactId"""
        if ':' in package_str:
            parts = package_str.split(':')
            if len(parts) >= 2:
                return {"groupId": parts[0], "artifactId": parts[1]}
        return {"groupId": "", "artifactId": package_str}

    def _read_package_list(self, file_finding: FileFinding) -> List[str]:
        """Read package list from the file finding"""
        # For package-list type, the path contains the actual package names
        return file_finding.path.split(',') if file_finding.path else []

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """Scan maven packages for unclaimed status"""
        package_strings = self._read_package_list(file_finding)
        
        if not package_strings:
            return []

        # Convert to Maven format expected by package checker
        maven_packages = [self._parse_maven_package(pkg) for pkg in package_strings]
        
        # Check packages asynchronously
        package_exists_results = await check_packages_async(maven_packages, "maven")
        
        # Create findings for unclaimed packages
        findings = []
        for i, (original_pkg, exists) in enumerate(zip(package_strings, package_exists_results)):
            if not exists:
                finding = PackageFinding(
                    name=original_pkg,
                    file_path=file_finding.path,
                    scan_type=ScanType.MAVEN_PACKAGE_LIST,
                    language=self.supported_language,
                    severity="warning",
                    message=f"Package '{original_pkg}' is unclaimed in Maven registry and publicly available for anyone to register.",
                    start_line=i + 1,
                    end_line=i + 1
                )
                findings.append(finding)
        
        return findings
