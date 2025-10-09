from typing import List, Dict
import os
import json
import re
from .base import BaseExecutor
from ..models.models import FileFinding, PackageFinding, ScanType
from ..utils.package_checker import check_packages_async

class PackageJsonExecutor(BaseExecutor):
    """Executor for checking JavaScript package.json files and their scopes"""
    
    supported_language = "javascript"
    supported_file_types = ["package_json"]
    
    def __init__(self, project_root):
        super().__init__(project_root)

    def should_scan_file(self, file_finding: FileFinding) -> bool:
        """Check if this is a JavaScript package.json file"""
        return (file_finding.language == self.supported_language and 
                file_finding.file_type in self.supported_file_types)

    def _parse_package_json(self, file_path: str) -> Dict:
        """Parse package.json file and return its contents"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Error parsing package.json at {file_path}: {str(e)}")

    def _extract_actual_package_name(self, alias_name: str, version_spec: str) -> str:
        """
        Extract the actual package name from npm alias or version specification.
        
        Args:
            alias_name (str): The alias/key name from package.json
            version_spec (str): The version specification from package.json
            
        Returns:
            str: The actual package name to check
        """
        if not isinstance(version_spec, str):
            return alias_name
            
        version_spec = version_spec.strip()
        
        # Handle npm aliasing: "alias": "npm:actual-package@version"
        if version_spec.startswith('npm:'):
            # Extract package name from npm:package@version or npm:@scope/package@version
            npm_spec = version_spec[4:]  # Remove 'npm:' prefix
            if npm_spec.startswith('@'):
                # Scoped package: @scope/package@version -> @scope/package
                parts = npm_spec.split('@')
                if len(parts) >= 3:  # @, scope/package, version
                    package_name = f"@{parts[1]}"
                else:
                    package_name = npm_spec.split('@')[0] if '@' in npm_spec[1:] else npm_spec
            else:
                # Regular package: package@version -> package
                package_name = npm_spec.split('@')[0]
            
            # Filter out packages with invalid characters for npm (only allow a-z, A-Z, 0-9, -, _, @, /)
            if not re.match(r'^[@a-zA-Z0-9_/-]+$', package_name):
                return ""
                
            return package_name
        
        # If not an npm alias, use the original alias name
        package_name = alias_name
        
        # Filter out packages with invalid characters for npm (only allow a-z, A-Z, 0-9, -, _, @, /)
        if not re.match(r'^[@a-zA-Z0-9_/-]+$', package_name):
            return ""
            
        return package_name

    def _is_npm_registry_dependency(self, version_spec: str) -> bool:
        """
        Check if a dependency version specification indicates it comes from npm registry.
        Returns False for GitHub repos, Git URLs, file paths, workspace deps, etc.
        
        Args:
            version_spec (str): The version specification from package.json
            
        Returns:
            bool: True if this is likely an npm registry dependency
        """
        if not isinstance(version_spec, str):
            return True  # Assume npm if not a string
            
        version_spec = version_spec.strip()
        
        # npm aliasing is always from npm registry
        if version_spec.startswith('npm:'):
            return True
        
        # Workspace dependencies (monorepo internal dependencies)
        if version_spec.startswith('workspace:'):
            return False
        
        # GitHub repository references
        if version_spec.startswith('github:') or version_spec.startswith('git+'):
            return False
            
        # Direct Git URLs
        if any(protocol in version_spec for protocol in ['git://', 'git+ssh://', 'git+https://', 'ssh://']):
            return False
            
        # HTTP/HTTPS URLs (tarball downloads)
        if version_spec.startswith(('http://', 'https://')):
            return False
            
        # File paths (local dependencies)
        if version_spec.startswith(('file:', './', '../', '/')):
            return False
            
        # GitHub shorthand (user/repo or user/repo#tag)
        if '/' in version_spec and not version_spec.startswith('@'):
            # This might be GitHub shorthand like "user/repo" or "user/repo#tag"
            # But we need to be careful not to filter out scoped packages like "@scope/package"
            return False
            
        # If none of the above patterns match, assume it's an npm registry dependency
        return True

    async def scan_file_async(self, file_finding: FileFinding) -> List[PackageFinding]:
        """
        Scan package.json file for dependencies and check their scopes asynchronously
        
        Args:
            file_finding (FileFinding): Information about the file to scan
            
        Returns:
            List[PackageFinding]: Results of the scan
        """
        file_path = os.path.join(self.project_root, file_finding.path)
        package_data = self._parse_package_json(file_path)
        findings = []
        
        if not package_data:
            return findings

        # Combine dependencies and devDependencies
        all_dependencies = {}
        all_dependencies.update(package_data.get('dependencies', {}))
        all_dependencies.update(package_data.get('devDependencies', {}))
        all_dependencies.update(package_data.get('optionalDependencies', {}))

        # Filter out dependencies that are not from npm registry and extract actual package names
        npm_dependencies = {}
        alias_to_actual = {}  # Map from alias to actual package name
        for alias_name, version_spec in all_dependencies.items():
            if self._is_npm_registry_dependency(version_spec):
                actual_package_name = self._extract_actual_package_name(alias_name, version_spec)
                if actual_package_name:  # Only process if valid package name
                    npm_dependencies[actual_package_name] = version_spec
                    alias_to_actual[actual_package_name] = alias_name

        package_exists_results = await check_packages_async(npm_dependencies.keys(), "npm")
        for package_name, exists in zip(npm_dependencies.keys(), package_exists_results):
            if not exists:
                # Use the original alias name in the finding for better context
                original_alias = alias_to_actual.get(package_name, package_name)
                findings.append(PackageFinding(
                    name=package_name,
                    file_path=file_finding.path,
                    scan_type=ScanType.JS_PACKAGE_JSON,
                    language=self.supported_language,
                    start_line=1,
                    end_line=1,
                    code_snippet=f"Package '{package_name}' is unclaimed and publicly available for anyone to register."
                ))

        return findings