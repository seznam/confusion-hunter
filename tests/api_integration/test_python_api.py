"""
Integration tests for the Python API as documented in README.md
"""
import pytest
import tempfile
import os
from pathlib import Path
import sys
import json

# Import the professional module names
import confusion_hunter.scanner as scanner
from confusion_hunter.models.models import ScanResult, PackageFinding, FileFinding
from confusion_hunter.utils.package_checker import check_packages_sync


class TestPythonAPI:
    """Test the Python API as documented in the README"""

    def test_import_scanner_module(self):
        """Test that the scanner module can be imported as documented"""
        # Professional import path: import confusion_hunter.scanner as scanner
        assert hasattr(scanner, 'run_scanner')
        assert hasattr(scanner, 'setup_scanner')

    def test_run_scanner_basic(self):
        """Test the basic run_scanner function with a temporary project"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple requirements.txt with a likely unclaimed package
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("definitely-does-not-exist-package==1.0.0\n")
            
            # Run scanner
            result = scanner.run_scanner(temp_dir)
            
            # Verify result structure
            assert isinstance(result, ScanResult)
            assert hasattr(result, 'findings')
            assert hasattr(result, 'unclaimed_packages')
            assert isinstance(result.findings, list)
            assert isinstance(result.unclaimed_packages, list)
            
            # Should find the requirements.txt file
            assert len(result.findings) >= 1
            assert any(f.path.endswith('requirements.txt') for f in result.findings)

    def test_setup_scanner_advanced(self):
        """Test the advanced setup_scanner approach"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            package_json = Path(temp_dir) / "package.json"
            package_json.write_text('{"dependencies": {"react": "^17.0.0"}}')
            
            # Test advanced usage
            scanner_instance = scanner.setup_scanner(project_root=temp_dir)
            files = scanner_instance.find_config_files()
            unclaimed = scanner_instance.scan_files(files)
            
            # Verify structure
            assert isinstance(files, list)
            assert isinstance(unclaimed, list)
            assert len(files) >= 2  # Should find both files

    def test_package_checker_direct_usage(self):
        """Test the package checker as documented in README"""
        # Test with a mix of real and fake packages
        packages = ["requests", "numpy", "definitely-does-not-exist-package-12345"]
        
        # Test the documented API
        claimed_status = check_packages_sync(packages, "pypi")
        
        assert isinstance(claimed_status, list)
        assert len(claimed_status) == len(packages)
        assert all(isinstance(status, bool) for status in claimed_status)
        
        # requests and numpy should exist (True), fake package should not (False)
        assert claimed_status[0] is True  # requests
        assert claimed_status[1] is True  # numpy
        assert claimed_status[2] is False  # fake package

    def test_scan_result_methods(self):
        """Test ScanResult methods and output formats"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple test case
            requirements_file = Path(temp_dir) / "requirements.txt" 
            requirements_file.write_text("fake-package-name-12345==1.0.0\n")
            
            result = scanner.run_scanner(temp_dir)
            
            # Test summary methods
            summary = result.get_summary()
            assert isinstance(summary, dict)
            
            # Test output formats
            dict_output = result.to_dict()
            assert isinstance(dict_output, dict)
            assert 'findings' in dict_output
            assert 'unclaimed_packages' in dict_output
            
            sarif_output = result.to_sarif()
            assert isinstance(sarif_output, dict)
            assert '$schema' in sarif_output
            assert 'runs' in sarif_output

    def test_pathlib_usage(self):
        """Test that Path objects work as documented"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # Create test file
            requirements_file = project_root / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            # Test with Path object
            result = scanner.run_scanner(project_root)
            
            assert isinstance(result, ScanResult)
            assert len(result.findings) >= 1


class TestMissingFunctionality:
    """Test for functionality mentioned in README but potentially missing"""

    def test_check_unclaimed_packages_function(self):
        """Test if check_unclaimed_packages function exists as documented"""
        # The README mentions: hunter.check_unclaimed_packages(packages, "pip")
        # This function should now exist
        
        assert hasattr(scanner, 'check_unclaimed_packages')
        
        packages = ["requests", "fake-package-12345"]
        result = scanner.check_unclaimed_packages(packages, "pip")
        
        # Test the result structure
        assert hasattr(result, 'unclaimed_packages')
        assert hasattr(result, 'findings')
        assert isinstance(result.unclaimed_packages, list)
        assert isinstance(result.findings, list)
        
        # Should have at least one fake package as unclaimed
        fake_packages = [pkg for pkg in result.unclaimed_packages if pkg.name == "fake-package-12345"]
        assert len(fake_packages) >= 1


class TestErrorHandling:
    """Test error handling in the API"""

    def test_invalid_project_path(self):
        """Test behavior with invalid project paths"""
        # The scanner gracefully handles invalid paths by returning empty results
        result = scanner.run_scanner("/definitely/does/not/exist")
        
        assert isinstance(result, ScanResult)
        assert len(result.findings) == 0
        assert len(result.unclaimed_packages) == 0

    def test_empty_project(self):
        """Test behavior with empty project directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = scanner.run_scanner(temp_dir)
            
            assert isinstance(result, ScanResult)
            assert len(result.findings) == 0
            assert len(result.unclaimed_packages) == 0

    def test_invalid_package_registry(self):
        """Test package checker with invalid registry"""
        packages = ["requests"]
        
        with pytest.raises(ValueError):
            check_packages_sync(packages, "invalid_registry")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
