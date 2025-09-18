"""
Integration tests for the CLI interface as documented in README.md
"""
import pytest
import tempfile
import subprocess
import os
import json
from pathlib import Path

# Get the project root directory dynamically
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


class TestCLIInterface:
    """Test CLI commands as documented in README"""

    def test_confusion_hunter_help(self):
        """Test that confusion-hunter --help works"""
        result = subprocess.run(
            ["confusion-hunter", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        assert "confusion-hunter" in result.stdout
        assert "project_root" in result.stdout

    def test_hunter_help(self):
        """Test that hunter --help works"""
        result = subprocess.run(
            ["hunter", "--help"],
            capture_output=True, 
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        assert "project_root" in result.stdout

    def test_basic_project_scan(self):
        """Test basic project scanning with confusion-hunter"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test requirements file
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--stdout", "--raw"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            assert result.returncode == 0
            
            # Should return valid JSON
            output_data = json.loads(result.stdout)
            assert "findings" in output_data
            assert "unclaimed_packages" in output_data

    def test_pretty_output(self):
        """Test --pretty flag"""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--stdout", "--pretty", "--raw"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            assert result.returncode == 0
            # Pretty output should have indentation
            assert "    " in result.stdout or "  " in result.stdout

    def test_sarif_output_default(self):
        """Test that SARIF is the default output format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--stdout"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            assert result.returncode == 0
            
            # Should be SARIF format
            output_data = json.loads(result.stdout)
            assert "$schema" in output_data
            assert "runs" in output_data

    def test_output_to_file(self):
        """Test --output flag"""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            output_file = Path(temp_dir) / "output.json"
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--output", str(output_file), "--raw"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            assert result.returncode == 0
            assert output_file.exists()
            
            # Verify file content
            with open(output_file) as f:
                data = json.load(f)
            assert "findings" in data
            assert "unclaimed_packages" in data


class TestUnclaimedPackageChecking:
    """Test unclaimed package checking CLI functionality"""

    def test_unclaimed_pip_packages(self):
        """Test checking specific pip packages"""
        result = subprocess.run(
            ["hunter", "--unclaimed", "pip", "requests", "fake-package-name-12345", "--stdout", "--raw", "--quiet"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        
        # Should return valid JSON
        output_data = json.loads(result.stdout)
        assert "unclaimed_packages" in output_data

    def test_unclaimed_npm_packages(self):
        """Test checking specific npm packages"""
        result = subprocess.run(
            ["hunter", "--unclaimed", "npm", "react", "fake-npm-package-12345", "--stdout", "--raw", "--quiet"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        
        # Should return valid JSON
        output_data = json.loads(result.stdout)
        assert "unclaimed_packages" in output_data

    def test_pip_freeze_input(self):
        """Test pip freeze input via stdin"""
        pip_freeze_output = "requests==2.25.0\nnumpy==1.21.0\nfake-package-12345==1.0.0\n"
        
        result = subprocess.run(
            ["hunter", "--unclaimed", "pip", "--stdout", "--raw", "--quiet"],
            input=pip_freeze_output,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        
        # Should return valid JSON
        output_data = json.loads(result.stdout)
        assert "unclaimed_packages" in output_data

    def test_quiet_mode(self):
        """Test --quiet flag"""
        result = subprocess.run(
            ["hunter", "--unclaimed", "pip", "requests", "--quiet", "--stdout", "--raw"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0
        # In quiet mode, stderr should be minimal
        assert len(result.stderr.strip()) == 0 or "Checking" not in result.stderr


class TestPipelineFeatures:
    """Test pipeline-specific CLI features"""

    def test_fail_on_found_success(self):
        """Test --fail-on-found with no unclaimed packages"""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")  # Real package
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--fail-on-found", "--quiet"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            # Should succeed (exit code 0) if no unclaimed packages
            assert result.returncode == 0

    def test_fail_on_found_failure(self):
        """Test --fail-on-found with unclaimed packages"""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("definitely-fake-package-12345==1.0.0\n")  # Fake package
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--fail-on-found", "--quiet"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            # Should fail (exit code 1) if unclaimed packages found
            assert result.returncode == 1

    def test_summary_only(self):
        """Test --summary-only flag"""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.25.0\n")
            
            result = subprocess.run(
                ["confusion-hunter", temp_dir, "--summary-only"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            assert result.returncode == 0
            # Should show summary information
            assert "Scan Summary" in result.stdout or "Total unclaimed packages" in result.stdout


class TestErrorHandling:
    """Test CLI error handling"""

    def test_invalid_project_path(self):
        """Test CLI with invalid project path"""
        result = subprocess.run(
            ["confusion-hunter", "/definitely/does/not/exist"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        # CLI gracefully handles invalid paths by returning empty results
        assert result.returncode == 0
        assert "Found 0 configuration files" in result.stdout

    def test_missing_project_root(self):
        """Test CLI without project_root when not using --unclaimed"""
        result = subprocess.run(
            ["confusion-hunter"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        # Should return error exit code
        assert result.returncode == 2
        assert "project_root is required" in result.stderr

    def test_unclaimed_without_packages(self):
        """Test --unclaimed without providing packages"""
        result = subprocess.run(
            ["hunter", "--unclaimed", "pip"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        # Should return error exit code
        assert result.returncode == 2
        assert "No packages provided" in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
