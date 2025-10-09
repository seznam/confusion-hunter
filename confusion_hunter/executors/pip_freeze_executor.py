from typing import List
import re
import sys
from .base import BaseExecutor
from ..utils.package_checker import check_packages_async
from ..models.models import FileFinding, PackageFinding, ScanType


class PipFreezeExecutor(BaseExecutor):
    """Executor for handling pip freeze input from stdin or direct package lists"""

    supported_language = "python"
    supported_file_types = ["pip-freeze", "package-list"]

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    def _parse_pip_freeze_line(self, line: str) -> str:
        """Parse a single pip freeze line to extract package name"""
        line = line.strip()
        if line and not line.startswith('#'):
            # Parse package name from pip freeze format (package==version)
            match = re.match(r'^([a-zA-Z0-9_.-]+)', line)
            if match:
                return match.group(1)
        return None

    def _normalize_package_name(self, package_name: str) -> str:
        """Normalize package name for PyPI (lowercase, replace underscores/dots with hyphens)"""
        return re.sub(r'[-_.]+', '-', package_name.lower())

    def _read_stdin_content(self) -> List[str]:
        """Read and parse packages from stdin"""
        packages = []
        if not sys.stdin.isatty():  # Check if there's piped input
            for line in sys.stdin:
                package = self._parse_pip_freeze_line(line)
                if package:
                    packages.append(package)
        return packages

    def _read_file_content(self, file_finding: FileFinding) -> List[str]:
        """Read and parse packages from a file or return package list"""
        if file_finding.file_type == "package-list":
            # For package-list type, the path contains the actual package names
            # This is used when packages are passed directly via CLI
            return file_finding.path.split(',') if file_finding.path and file_finding.path != "stdin" else []
        elif file_finding.file_type == "pip-freeze":
            # For pip-freeze type, read from stdin
            return self._read_stdin_content()
        else:
            # Fallback: try to read as a file
            content = self._read_file(file_finding)
            packages = []
            for line in content.split('\n'):
                package = self._parse_pip_freeze_line(line)
                if package:
                    packages.append(package)
            return packages

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """Scan packages for unclaimed status"""
        packages = self._read_file_content(file_finding)
        
        if not packages:
            return []

        # Normalize package names for PyPI
        normalized_packages = [self._normalize_package_name(pkg) for pkg in packages]
        
        # Check packages asynchronously
        package_exists_results = await check_packages_async(normalized_packages, "pypi")
        
        # Create findings for unclaimed packages
        findings = []
        for i, (original_pkg, exists) in enumerate(zip(packages, package_exists_results)):
            if not exists:
                finding = PackageFinding(
                    name=original_pkg,
                    file_path=file_finding.path,
                    scan_type=ScanType.PYTHON_PIP_FREEZE,
                    language=self.supported_language,
                    severity="warning",
                    message=f"Package '{original_pkg}' is unclaimed in PIP registry and publicly available for anyone to register.",
                    start_line=i + 1,  # Line number for the package
                    end_line=i + 1
                )
                findings.append(finding)
        
        return findings
