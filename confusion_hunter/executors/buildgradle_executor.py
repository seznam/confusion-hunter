from typing import List, Set
import os
import re
from .base import BaseExecutor
from ..models.models import FileFinding, PackageFinding, ScanType
from ..utils.package_checker import check_packages_async
from .package_parsers.buildgradle_parser import BuildGradleParser

class BuildGradleExecutor(BaseExecutor):
    """Executor for checking Gradle build.gradle files"""
    
    supported_language = "java"
    supported_file_types = ["buildgradle"]
    
    def __init__(self, project_root):
        super().__init__(project_root)

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        """Check if this is a Gradle build file"""
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Scan build.gradle file for dependencies asynchronously
        
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
            
            # Get the full path to the file
            file_path = os.path.join(self.project_root, file_finding.path)
            
            # Use the BuildGradleParser to extract package information
            packages = BuildGradleParser.get_packages(file_path)
            
            # Check if there are any packages to check
            if not packages:
                return findings
            
            # Prepare packages for checking by creating a simplified dict with just groupId and artifactId
            # We'll keep track of the mapping between resolved and raw versions
            check_packages = []
            mapping = {}  # Maps (groupId, resolved_artifactId) to original raw package
            
            for pkg in packages:
                group_id = pkg.get('groupId', '')
                resolved_artifact_id = pkg.get('artifactId', '')
                raw_artifact_id = pkg.get('rawArtifactId', resolved_artifact_id)
                
                check_pkg = {'groupId': group_id, 'artifactId': resolved_artifact_id}
                check_packages.append(check_pkg)
                
                # Store mapping to original raw package
                mapping[(group_id, resolved_artifact_id)] = {'groupId': group_id, 'artifactId': raw_artifact_id}
            
            # Deduplicate packages by groupId:artifactId
            unique_packages = []
            seen_packages = set()
            
            for pkg in check_packages:
                package_key = f"{pkg.get('groupId', '')}:{pkg.get('artifactId', '')}"
                if package_key not in seen_packages:
                    seen_packages.add(package_key)
                    unique_packages.append(pkg)
            
            # Check all packages asynchronously in one batch
            package_exists_results = await check_packages_async(unique_packages, "maven")
            
            # Process results
            for package, exists in zip(unique_packages, package_exists_results):
                if not exists:
                    group_id = package.get('groupId', '')
                    resolved_artifact_id = package.get('artifactId', '')
                    
                    # Get the original raw package
                    raw_pkg = mapping.get((group_id, resolved_artifact_id), package)
                    raw_artifact_id = raw_pkg.get('artifactId', resolved_artifact_id)
                    
                    # Find line numbers where the dependency is defined
                    start_line = 1  # Default if we can't find it
                    end_line = 1
                    code_snippet = None
                    
                    # Look for the dependency in the file content
                    for i, line in enumerate(lines):
                        if f"'{group_id}:{raw_artifact_id}" in line or f"\"{group_id}:{raw_artifact_id}" in line:
                            start_line = i + 1  # Convert to 1-based line number
                            end_line = i + 1
                            code_snippet = line.strip()
                            break
                    
                    # If not found with that pattern, try to find with other patterns
                    if not code_snippet:
                        for i, line in enumerate(lines):
                            if group_id in line and raw_artifact_id in line:
                                start_line = i + 1
                                end_line = i + 1
                                code_snippet = line.strip()
                                break
                    
                    # If still not found, create a generic snippet
                    if not code_snippet:
                        code_snippet = f"implementation '{group_id}:{raw_artifact_id}:<version>'"
                    
                    # Include both original and resolved version information in the message
                    message = f"Package is unclaimed and publicly available for anyone to register."
                    if raw_artifact_id != resolved_artifact_id:
                        message = f"Package '{group_id}:{raw_artifact_id}' (resolved to '{group_id}:{resolved_artifact_id}') is unclaimed and publicly available for anyone to register."
                    
                    findings.append(PackageFinding(
                        name=f"{group_id}:{raw_artifact_id}",  # Use raw artifact ID for reporting
                        file_path=file_finding.path,
                        scan_type=ScanType.GRADLE_BUILDGRADLE,
                        language=self.supported_language,
                        start_line=start_line,
                        end_line=end_line,
                        code_snippet=code_snippet,
                        message=message
                    ))
                    
        except Exception as e:
            print(f"Error scanning {file_finding.path}: {type(e).__name__}: {str(e)}")
            
        return findings