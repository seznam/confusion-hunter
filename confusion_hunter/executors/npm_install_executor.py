from typing import List
from ..models.models import FileFinding, PackageFinding, ScanType
from .base import BaseExecutor
from .package_parsers.npm_parser import NPMParser
from ..utils.package_checker import check_packages_async


class NPMInstallExecutor(BaseExecutor):

    supported_language = "javascript"
    supported_file_types = ["dockerfile", "gitlab-ci", "script"]

    npm_parser = NPMParser()

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        return file_finding.language == self.supported_language and file_finding.file_type in self.supported_file_types

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        content = self._read_file(file_finding)

        installs = self.npm_parser.get_packages(content, file_finding.file_type)
        findings = []
        
        # Process each install command separately to maintain line number accuracy
        for install in installs:
            package_exists_results = await check_packages_async(install.packages, "npm")
            for package, exists in zip(install.packages, package_exists_results):
                # Check if package exists
                if not exists:
                    findings.append(PackageFinding(
                        name=package,
                        file_path=file_finding.path,
                        scan_type=ScanType.JS_NPM,
                        language=self.supported_language,
                        start_line=install.line_numbers[0],
                        end_line=install.line_numbers[1],
                        code_snippet=install.snippet
                    ))
                
        return findings
