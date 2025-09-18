import os
from typing import List, Dict, Type
from .models.models import FileFinding, ScanResult
from .detectors.base import BaseDetector
from .executors.base import BaseExecutor

class ExecutionManager:
    """Manages the execution of detectors and executors"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.detectors: List[BaseDetector] = []
        self.executors: Dict[str, List[BaseExecutor]] = {}
        self.processed_files: Dict[str, List[FileFinding]] = {}

    def register_detector(self, detector: BaseDetector):
        """Register a new detector"""
        self.detectors.append(detector)
    
    def register_detectors(self, detectors: List[BaseDetector]):
        """Register a list of detectors"""
        self.detectors.extend(detectors)

    def register_executor(self, language: str, executor: BaseExecutor):
        """Register a new executor for a specific language"""
        if language not in self.executors:
            self.executors[language] = []
        self.executors[language].append(executor)

    def register_executors_by_language(self, language: str, executors: List[BaseExecutor]):
        """Register a list of executors for a specific language"""
        if language not in self.executors:
            self.executors[language] = []
        self.executors[language].extend(executors)

    def find_config_files(self) -> List[FileFinding]:
        """Find all configuration files in the project"""
        findings = []

        # Files and directories to exclude from scanning
        excluded_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin', '.class'}
        excluded_dirs = {'__pycache__', '.git', '.svn', '.hg', '.bzr', 'node_modules', '.venv', 'venv'}

        for dirpath, dirnames, filenames in os.walk(self.project_root):
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            
            for filename in filenames:
                # Skip files with excluded extensions
                if any(filename.endswith(ext) for ext in excluded_extensions):
                    continue
                    
                file_path = os.path.join(dirpath, filename)
                
                if not os.path.isfile(file_path):
                    continue
                
                for detector in self.detectors:
                    match = detector.match_file(filename)
                    if match:
                        rel_path = os.path.relpath(file_path, self.project_root)
                        if os.path.isabs(self.project_root):
                            # For absolute project_root, join it with relative path
                            findings.append(detector.create_finding(
                                os.path.join(self.project_root, rel_path),
                                match
                            ))
                        else:
                            # For relative project_root, keep path relative
                            findings.append(detector.create_finding(
                                rel_path,
                                match
                            ))
        return findings

    def scan_files(self, findings: List[FileFinding]):
        """Scan files for unclaimed packages"""
        unclaimed_packages = []
        self.processed_files.clear()  # Reset processed files for new scan

        for file_info in findings:
            file_dir = os.path.dirname(file_info.path)
            
            # Initialize directory in processed_files if not exists
            if file_dir not in self.processed_files:
                self.processed_files[file_dir] = []
                
            # Get executors for this file's language
            executors = self.executors.get(file_info.language, [])
            
            # Run each executor that should scan this file
            for executor in executors:
                if executor.should_scan_file(file_info):
                    unclaimed_packages.extend(executor.scan_file(file_info))
                    
            # Mark this file as processed
            self.processed_files[file_dir].append(file_info)

        return unclaimed_packages

    def run_scan(self) -> ScanResult:
        """Run the complete scan"""
        findings = self.find_config_files()
        unclaimed_packages = self.scan_files(findings)
        return ScanResult(findings=findings, unclaimed_packages=unclaimed_packages) 