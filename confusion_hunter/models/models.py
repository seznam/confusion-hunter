from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
import os

class ScanType(Enum):
    """Types of scans we can perform"""
    PYTHON_REQUIREMENTS = "python-requirements"
    PYTHON_PIP = "python-pip"
    PYTHON_UVLOCK = "python-uvlock"
    PYTHON_POETRYLOCK = "python-poetrylock"
    PYTHON_PYPROJECT = "python-pyproject"
    PYTHON_PIPFILE = "python-pipfile"  # Added missing enum for Pipfile
    PYTHON_PIP_FREEZE = "python-pip-freeze"  # Added for pip freeze input
    JS_PACKAGE_JSON = "js-package-json"
    JS_NPM = "js-npm"
    JS_PACKAGE_LIST = "js-package-list"  # Added for npm package list
    MAVEN_POMXML = "maven-pomxml"  # Added new enum for Maven POM XML
    MAVEN_PACKAGE_LIST = "maven-package-list"  # Added for maven package list
    GRADLE_BUILDGRADLE = "gradle-buildgradle"  # Added new enum for Gradle build files

@dataclass
class FileFinding:
    """Represents a detected configuration file"""
    path: str
    language: str
    file_type: str

@dataclass
class PackageFinding:
    """Represents a single package finding"""
    name: str
    file_path: str
    scan_type: ScanType
    language: str  # Language determined by the executor (e.g., "python", "javascript", "java")
    severity: str = "warning"
    stage: str = "stage only"
    message: str = "Package is unclaimed and publicly available for anyone to register."
    report_type: str = "UNCLAIMED_PACKAGE"
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    code_snippet: Optional[str] = None

@dataclass
class ScanResult:
    """Represents the complete scan result"""
    findings: List[FileFinding]
    unclaimed_packages: List[PackageFinding]

    def get_summary(self) -> dict:
        """Get a summary of findings by scan type"""
        summary = {scan_type.value: 0 for scan_type in ScanType}
        for package in self.unclaimed_packages:
            summary[package.scan_type.value] += 1
        return summary

    def print_summary(self, quiet: bool = False):
        """Print a human-readable summary of findings"""
        summary = self.get_summary()
        total = sum(summary.values())
        
        if not quiet:
            print("\n[!] Scan Summary:")
            print(f"Total unclaimed packages found: {total}")
            for scan_type, count in summary.items():
                if count > 0:
                    print(f"- {scan_type}: {count} packages")
        
        return total
    
    def print_pipeline_summary(self):
        """Print a concise pipeline-friendly summary"""
        total = sum(self.get_summary().values())
        if total > 0:
            print(f"FAIL: {total} unclaimed packages detected")
            return False
        else:
            print("PASS: No unclaimed packages found")
            return True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "findings": [
                {
                    "path": f.path,
                    "type": f.language,
                    "file_type": f.file_type
                }
                for f in self.findings
            ],
            "unclaimed_packages": [
                {
                    "name": p.name,
                    "file": p.file_path,
                    "scan_type": p.scan_type.value,
                    "language": p.language,
                    "severity": p.severity,
                    "stage": p.stage,
                    "message": p.message,
                    "report_type": p.report_type,
                    "start_line": p.start_line,
                    "end_line": p.end_line,
                    "code_snippet": p.code_snippet
                }
                for p in sorted(self.unclaimed_packages, key=lambda x: (x.file_path, x.start_line or 0))
            ]
        }
    
    def to_sarif(self) -> Dict[str, Any]:
        """Convert to SARIF format for security analysis reporting"""
        # Create a mapping from file paths to FileFinding objects for metadata lookup
        file_metadata = {f.path: f for f in self.findings}
        
        # Calculate project root for relative paths
        project_root = os.getcwd()
        
        return {
            "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/schemas/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Dep-Conf-Scanner",
                            "fullName": "Dependency Confusion Scanner", 
                            "semanticVersion": "1.0.0",
                            "informationUri": "http://gsast.security.example.com/",
                            "rules": [
                                {
                                    "id": "UNCLAIMED_PACKAGE",
                                    "name": "Unclaimed Package",
                                    "shortDescription": {
                                        "text": "Unclaimed Package"
                                    },
                                    "fullDescription": {
                                        "text": "A package was found that is not available on a public registry, making it susceptible to dependency confusion attacks."
                                    },
                                    "help": {
                                        "text": "This package is not registered in the public repository. An attacker could claim this package name and publish a malicious version. Consumers of this package could then unknowingly install the malicious version. To remediate, either register the package name in the public repository or ensure that your package manager is configured to only use private repositories.",
                                        "markdown": "This package is not registered in the public repository. An attacker could claim this package name and publish a malicious version. Consumers of this package could then unknowingly install the malicious version. To remediate, either **register the package name** in the public repository or ensure that your package manager is configured to **only use private repositories**."
                                    },
                                    "properties": {
                                        "tags": [
                                            "security",
                                            "supply-chain"
                                        ],
                                        "precision": "high"
                                    }
                                }
                            ]
                        }
                    },
                    "results": [
                        self._create_sarif_result(p, file_metadata.get(p.file_path), project_root)
                        for p in sorted(self.unclaimed_packages, key=lambda x: (x.file_path, x.start_line or 0))
                    ]
                }
            ]
        }
    
    def _create_sarif_result(self, package: 'PackageFinding', file_finding: Optional['FileFinding'], project_root: str) -> Dict[str, Any]:
        """Create a single SARIF result with enhanced metadata"""
        # Convert to relative path
        relative_path = self._get_relative_path(package.file_path, project_root)
        
        # Get absolute path
        absolute_path = os.path.abspath(package.file_path)
        
        # Get file metadata
        file_type = file_finding.file_type if file_finding else "unknown"
        
        # Create enhanced message with file context
        base_message = f"Package '{package.name}' is unclaimed and publicly available for anyone to register."
        enhanced_message = f"{base_message} Found in {package.language} {file_type} file."
        
        return {
            "ruleId": package.report_type,
            "level": "warning" if package.severity == "warning" else "error",
            "message": {
                "text": enhanced_message
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": relative_path
                        },
                        "region": {
                            "startLine": package.start_line or 1,
                            "endLine": package.end_line or package.start_line or 1,
                            "snippet": {
                                "text": package.code_snippet or f"Package '{package.name}' is unclaimed and publicly available for anyone to register."
                            }
                        }
                    }
                }
            ],
            "properties": {
                "language": package.language,
                "fileType": file_type,
                "scanType": package.scan_type.value,
                "packageName": package.name,
                "relativePath": relative_path,
                "absolutePath": absolute_path
            },
            "relatedLocations": []
        }
    
    def _get_relative_path(self, file_path: str, project_root: str) -> str:
        """Convert absolute path to relative path, ensuring no leading slash"""
        try:
            # If already relative, return as-is (but ensure no leading slash)
            if not os.path.isabs(file_path):
                return file_path.lstrip('/')
            
            # Convert absolute to relative
            rel_path = os.path.relpath(file_path, project_root)
            
            # Ensure no leading slash and use forward slashes
            rel_path = rel_path.replace('\\', '/').lstrip('/')
            
            return rel_path
        except (ValueError, OSError):
            # Fallback: just remove leading slash from original path
            return file_path.lstrip('/')
