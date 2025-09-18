"""
Test all examples from README.md to ensure they work correctly
"""
import pytest
import tempfile
import subprocess
import os
import json
from pathlib import Path
import sys

# Get the project root directory dynamically
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Import the professional module names
import confusion_hunter.scanner as hunter
from confusion_hunter.utils.package_checker import check_packages_sync


class TestREADMEExamples:
    """Test all the code examples from the README"""

    def test_readme_basic_import_example(self):
        """Test the basic import example from README"""
        # Professional import as shown in README: import confusion_hunter.scanner as hunter
        
        assert hasattr(hunter, 'run_scanner')
        assert hasattr(hunter, 'setup_scanner')
        assert hasattr(hunter, 'check_unclaimed_packages')

    def test_readme_quick_scan_example(self):
        """Test the quick scan example from README"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # Create a test file
            requirements_file = project_root / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            # README example: results = hunter.run_scanner(project_root)
            results = hunter.run_scanner(project_root)
            
            assert hasattr(results, 'findings')
            assert hasattr(results, 'unclaimed_packages')
            assert len(results.findings) >= 1

    def test_readme_advanced_scan_example(self):
        """Test the advanced scan example from README"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # Create test files
            requirements_file = project_root / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            # README example:
            # scanner = hunter.setup_scanner(project_root=project_root)
            # files = scanner.find_config_files()
            # unclaimed = scanner.scan_files(files)
            
            scanner = hunter.setup_scanner(project_root=str(project_root))
            files = scanner.find_config_files()
            unclaimed = scanner.scan_files(files)
            
            assert isinstance(files, list)
            assert isinstance(unclaimed, list)
            assert len(files) >= 1

    def test_readme_simple_results_example(self):
        """Test the simple results example from README"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_source_path = Path(temp_dir)
            
            # Create a test file
            requirements_file = project_source_path / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            # README example: results = hunter.run_scanner(project_source_path)
            results = hunter.run_scanner(project_source_path)
            
            assert hasattr(results, 'findings')
            assert hasattr(results, 'unclaimed_packages')

    def test_readme_check_unclaimed_packages_example(self):
        """Test the check_unclaimed_packages example from README"""
        # README example:
        # packages = ["requests", "numpy", "non-existing-package"]
        # result = hunter.check_unclaimed_packages(packages, "pip")
        # print(f"Found {len(result.unclaimed_packages)} unclaimed packages")
        
        packages = ["requests", "numpy", "fake-package-name-12345"]
        result = hunter.check_unclaimed_packages(packages, "pip")
        
        assert hasattr(result, 'unclaimed_packages')
        assert isinstance(result.unclaimed_packages, list)
        # Should find the fake package as unclaimed
        fake_packages = [pkg for pkg in result.unclaimed_packages if pkg.name == "fake-package-name-12345"]
        assert len(fake_packages) >= 1

    def test_readme_package_checker_example(self):
        """Test the package checker example from README"""
        # README example:
        # from confusion_hunter.utils.package_checker import check_packages_sync
        # claimed_status = check_packages_sync(packages, "pypi")
        
        packages = ["requests", "numpy", "fake-package-name-12345"]
        claimed_status = check_packages_sync(packages, "pypi")
        
        assert isinstance(claimed_status, list)
        assert len(claimed_status) == len(packages)
        assert all(isinstance(status, bool) for status in claimed_status)
        
        # requests and numpy should exist (True), fake package should not (False)
        assert claimed_status[0] is True  # requests
        assert claimed_status[1] is True  # numpy
        assert claimed_status[2] is False  # fake package


class TestREADMECLIExamples:
    """Test CLI examples from the README"""

    def test_readme_basic_cli_example(self):
        """Test basic CLI example: confusion-hunter ./my-repo --pretty --stdout"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--pretty", "--stdout", "--quiet"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            assert result.returncode == 0
            
            # Should return valid JSON (SARIF format by default)
            output_data = json.loads(result.stdout)
            assert "$schema" in output_data
            assert "runs" in output_data

    def test_readme_unclaimed_package_examples(self):
        """Test unclaimed package checking CLI examples from README"""
        
        # Example: hunter --unclaimed pip numpy requests non-existent-package
        result = subprocess.run(
            ["hunter", "--unclaimed", "pip", "requests", "fake-package-12345", "--quiet", "--stdout", "--raw"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert "unclaimed_packages" in output_data

    def test_readme_pip_freeze_example(self):
        """Test pip freeze example from README"""
        # Example: pip freeze | hunter --unclaimed pip
        pip_freeze_output = "requests==2.25.0\nnumpy==1.21.0\nfake-package-12345==1.0.0\n"
        
        result = subprocess.run(
            ["hunter", "--unclaimed", "pip", "--quiet", "--stdout", "--raw"],
            input=pip_freeze_output,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert "unclaimed_packages" in output_data

    def test_readme_npm_example(self):
        """Test NPM example from README"""
        # Example: hunter --unclaimed npm react lodash @my-org/private-package
        result = subprocess.run(
            ["hunter", "--unclaimed", "npm", "react", "fake-npm-package-12345", "--quiet", "--stdout", "--raw"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        output_data = json.loads(result.stdout)
        assert "unclaimed_packages" in output_data

    def test_readme_pipeline_examples(self):
        """Test pipeline examples from README"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with only real packages (should not fail)
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            # Example: confusion-hunter . --fail-on-found --quiet --summary-only
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--fail-on-found", "--quiet", "--summary-only"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            # Should succeed (exit code 0) since no unclaimed packages
            assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
