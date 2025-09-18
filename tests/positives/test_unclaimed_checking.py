import pytest
import sys
import io
from unittest.mock import patch, MagicMock
from confusion_hunter.scanner import parse_pip_freeze_input, create_virtual_file_finding, run_unclaimed_package_check
from confusion_hunter.models.models import ScanType, FileFinding
from confusion_hunter.executors.pip_freeze_executor import PipFreezeExecutor
from confusion_hunter.executors.npm_package_list_executor import NPMPackageListExecutor


class TestUnclaimedPackageChecking:
    """Test suite for unclaimed package checking functionality"""

    def test_parse_pip_freeze_input_with_packages(self):
        """Test parsing pip freeze output from stdin"""
        test_input = "requests==2.28.1\nnumpy==1.21.0\n# This is a comment\n"
        
        with patch('sys.stdin', io.StringIO(test_input)):
            with patch('sys.stdin.isatty', return_value=False):
                packages = parse_pip_freeze_input()
                
        assert packages == ['requests', 'numpy']

    def test_parse_pip_freeze_input_no_input(self):
        """Test parsing when no stdin input is available"""
        with patch('sys.stdin.isatty', return_value=True):
            packages = parse_pip_freeze_input()
            
        assert packages == []

    def test_create_virtual_file_finding_pip_stdin(self):
        """Test creating virtual file finding for pip with stdin input"""
        with patch('sys.stdin.isatty', return_value=False):
            file_finding = create_virtual_file_finding("pip", ["requests", "numpy"])
            
        assert file_finding.path == "stdin"
        assert file_finding.language == "python"
        assert file_finding.file_type == "pip-freeze"

    def test_create_virtual_file_finding_pip_args(self):
        """Test creating virtual file finding for pip with command line args"""
        with patch('sys.stdin.isatty', return_value=True):
            file_finding = create_virtual_file_finding("pip", ["requests", "numpy"])
            
        assert file_finding.path == "requests,numpy"
        assert file_finding.language == "python"
        assert file_finding.file_type == "package-list"

    def test_create_virtual_file_finding_npm(self):
        """Test creating virtual file finding for npm"""
        with patch('sys.stdin.isatty', return_value=True):
            file_finding = create_virtual_file_finding("npm", ["react", "lodash"])
            
        assert file_finding.path == "react,lodash"
        assert file_finding.language == "javascript"
        assert file_finding.file_type == "package-list"

    def test_create_virtual_file_finding_maven(self):
        """Test creating virtual file finding for maven"""
        with patch('sys.stdin.isatty', return_value=True):
            file_finding = create_virtual_file_finding("maven", ["org.apache:commons-lang3"])
            
        assert file_finding.path == "org.apache:commons-lang3"
        assert file_finding.language == "java"
        assert file_finding.file_type == "package-list"

    def test_pip_freeze_executor_package_list_parsing(self):
        """Test PipFreezeExecutor parsing package lists correctly"""
        executor = PipFreezeExecutor(".")
        file_finding = FileFinding(path="requests,numpy", language="python", file_type="package-list")
        
        packages = executor._read_file_content(file_finding)
        assert packages == ["requests", "numpy"]

    def test_pip_freeze_executor_normalization(self):
        """Test PipFreezeExecutor package name normalization"""
        executor = PipFreezeExecutor(".")
        
        assert executor._normalize_package_name("Django") == "django"
        assert executor._normalize_package_name("requests_oauthlib") == "requests-oauthlib"
        assert executor._normalize_package_name("package.name") == "package-name"

    def test_npm_package_list_executor_parsing(self):
        """Test NPMPackageListExecutor parsing package lists correctly"""
        executor = NPMPackageListExecutor(".")
        file_finding = FileFinding(path="react,lodash", language="javascript", file_type="package-list")
        
        packages = executor._read_package_list(file_finding)
        assert packages == ["react", "lodash"]

    @patch('confusion_hunter.scanner.ExecutionManager')
    def test_run_unclaimed_package_check_integration(self, mock_manager_class):
        """Test the integration of run_unclaimed_package_check"""
        # Mock the ExecutionManager and its methods
        mock_manager = MagicMock()
        mock_manager.scan_files.return_value = []  # No unclaimed packages found
        mock_manager_class.return_value = mock_manager
        
        with patch('sys.stdin.isatty', return_value=True):
            result = run_unclaimed_package_check([], ["requests"], "pip")
        
        # Verify ExecutionManager was created and scan_files was called
        mock_manager_class.assert_called_once_with(".")
        mock_manager.register_executors_by_language.assert_called_once()
        mock_manager.scan_files.assert_called_once()
        
        # Check result structure
        assert len(result.findings) == 1
        assert result.findings[0].language == "python"
        assert result.findings[0].file_type == "package-list"
        assert len(result.unclaimed_packages) == 0