import os
import json
import argparse
import sys
import re
from .manager import ExecutionManager
from .models.models import ScanResult, PackageFinding, ScanType, FileFinding
from .detectors import *
from .executors import *
from .utils.package_checker import check_packages_sync

def setup_scanner(project_root: str) -> ExecutionManager:
    """Set up the scanner with all detectors and executors"""
    manager = ExecutionManager(project_root)
    
    # Register detectors
    manager.register_detectors([
        PythonDetector,
        JavaScriptDetector,
        # MavenDetector,
        # GradleDetector
    ])
    
    # Register executors
    manager.register_executors_by_language("python", [
        PoetryLockExecutor(project_root),
        RequirementsExecutor(project_root),
        UvLockExecutor(project_root),
        PyprojectExecutor(project_root),
        PipfileExecutor(project_root),
        PIPInstallExecutor(project_root)
    ])

    manager.register_executors_by_language("javascript", [
        PackageJsonExecutor(project_root),
        NPMInstallExecutor(project_root)
    ])
    

    # currently we don't support java
    # it generates too many false positives
    # manager.register_executors_by_language("java", [
    #     PomXmlExecutor(project_root),
    #     BuildGradleExecutor(project_root)
    # ])
    
    return manager


def parse_pip_freeze_input():
    """Parse pip freeze output from stdin"""
    packages = []
    if not sys.stdin.isatty():  # Check if there's piped input
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse package name from pip freeze format (package==version)
                match = re.match(r'^([a-zA-Z0-9_.-]+)', line)
                if match:
                    packages.append(match.group(1))
    return packages

def create_virtual_file_finding(registry: str, packages: list, use_stdin: bool = None) -> FileFinding:
    """Create a virtual FileFinding for package list checking"""
    # Determine language and file type based on registry
    language_map = {
        "pip": "python",
        "npm": "javascript", 
        "maven": "java"
    }
    
    # Determine if we should use stdin mode
    if use_stdin is None:
        use_stdin = not sys.stdin.isatty()
    
    file_type_map = {
        "pip": "pip-freeze" if use_stdin else "package-list",
        "npm": "package-list",
        "maven": "package-list"
    }
    
    # For package lists, encode packages in the path (temporary solution)
    # For stdin, use "stdin" as path
    if use_stdin:
        path = "stdin"
    else:
        path = ",".join(packages)
    
    return FileFinding(
        path=path,
        language=language_map.get(registry, "unknown"),
        file_type=file_type_map.get(registry, "package-list")
    )

def run_unclaimed_package_check(packages_from_stdin: list, packages_from_args: list, registry: str) -> ScanResult:
    """Run unclaimed package checking using the executor pattern"""
    all_packages = packages_from_stdin + packages_from_args
    
    if not all_packages:
        return ScanResult(findings=[], unclaimed_packages=[])
    
    # Create virtual file finding - use stdin mode if we have stdin packages
    use_stdin = len(packages_from_stdin) > 0
    file_finding = create_virtual_file_finding(registry, all_packages, use_stdin=use_stdin)
    
    # Set up scanner with appropriate executors
    scanner = ExecutionManager(".")  # Use current directory as project root
    
    # Register the appropriate executor based on registry
    if registry == "pip":
        scanner.register_executors_by_language("python", [PipFreezeExecutor(".")])
    elif registry == "npm":
        scanner.register_executors_by_language("javascript", [NPMPackageListExecutor(".")])
    elif registry == "maven":
        scanner.register_executors_by_language("java", [MavenPackageListExecutor(".")])
    
    # Scan the virtual file
    unclaimed_packages = scanner.scan_files([file_finding])
    
    return ScanResult(findings=[file_finding], unclaimed_packages=unclaimed_packages)

# simple function to run the whole scanner
def run_scanner(project_root: str) -> ScanResult:
    scanner = setup_scanner(project_root)
    findings = scanner.find_config_files()
    unclaimed_packages = scanner.scan_files(findings)
    return ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)

def check_unclaimed_packages(packages: list, registry: str) -> ScanResult:
    """
    Check if specific packages are unclaimed in the given registry.
    
    This function provides a simple interface for checking package availability
    as documented in the README.
    
    Args:
        packages: List of package names to check
        registry: Registry to check against ("pip", "npm", or "maven")
        
    Returns:
        ScanResult: Result containing unclaimed packages
        
    Example:
        packages = ["requests", "numpy", "non-existent-package"]
        result = check_unclaimed_packages(packages, "pip")
        print(f"Found {len(result.unclaimed_packages)} unclaimed packages")
    """
    return run_unclaimed_package_check([], packages, registry)

def main():
    parser = argparse.ArgumentParser(description="Scan project for dependency confusion vulnerabilities.")
    parser.add_argument("project_root", nargs="?", help="Path to the root of the project.")
    parser.add_argument("--output", help="Path to output file.")
    parser.add_argument("--stdout", action="store_true", help="Print output to console.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output.")
    parser.add_argument("--relative", default=False, action="store_true", help="Use relative paths in output instead of absolute paths.")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON format instead of SARIF")
    
    # Unclaimed package checking options
    parser.add_argument("--unclaimed", choices=["pip", "npm", "maven"], 
                       help="Check if specific packages are unclaimed in the given registry")
    parser.add_argument("packages", nargs="*", 
                       help="Package names to check (when using --unclaimed)")
    
    # Pipeline-specific options
    parser.add_argument("--fail-on-found", action="store_true", 
                       help="Exit with code 1 if unclaimed packages are found (useful for CI/CD pipelines)")
    parser.add_argument("--expect-findings", action="store_true",
                       help="Invert exit code logic - exit with code 1 if NO unclaimed packages found (useful for self-testing)")
    parser.add_argument("--quiet", action="store_true", 
                       help="Suppress all output except errors (useful for CI/CD pipelines)")
    parser.add_argument("--summary-only", action="store_true",
                       help="Only show summary, no detailed findings")
    
    args = parser.parse_args()

    # Handle unclaimed package checking mode
    if args.unclaimed:
        # Collect packages from stdin (pip freeze) and command line arguments
        packages_from_stdin = parse_pip_freeze_input()
        packages_from_args = args.packages or []
        
        # If project_root was provided but we're in unclaimed mode, treat it as a package name
        if args.project_root and args.project_root not in ['.', '..'] and not os.path.isdir(args.project_root):
            packages_from_args.insert(0, args.project_root)
        
        if not packages_from_stdin and not packages_from_args:
            print("Error: No packages provided. Use 'pip freeze | hunter --unclaimed pip' or 'hunter --unclaimed pip package1 package2'", file=sys.stderr)
            sys.exit(2)
        
        total_packages = len(packages_from_stdin) + len(packages_from_args)
        if not args.quiet:
            print(f"[*] Checking {total_packages} packages against {args.unclaimed.upper()} registry...")
        
        result = run_unclaimed_package_check(packages_from_stdin, packages_from_args, args.unclaimed)
        
        if not args.quiet:
            print(f"[+] Found {len(result.unclaimed_packages)} unclaimed packages")
    else:
        # Regular project scanning mode
        if not args.project_root:
            print("Error: project_root is required when not using --unclaimed mode", file=sys.stderr)
            sys.exit(2)
        
        # Set up and run scanner
        if args.relative:
            project_root = os.path.relpath(args.project_root)
        else:
            project_root = os.path.abspath(args.project_root)
        
        scanner = setup_scanner(project_root=project_root)
        
        # Run scan and handle output
        if not args.quiet and not args.stdout:
            print(f"Scanning project at {project_root}")
            print("\n[*] Scanning project for configuration files...")
        findings = scanner.find_config_files()
        
        if not args.quiet and not args.stdout:
            print(f"[+] Found {len(findings)} configuration files")
            print("\n[*] Running package scanners...")
        unclaimed_packages = scanner.scan_files(findings)
        
        result = ScanResult(findings=findings, unclaimed_packages=unclaimed_packages)

    # Check for pipeline failure conditions
    if args.expect_findings:
        # Inverted logic: fail if NO unclaimed packages found (for self-testing)
        if len(result.unclaimed_packages) == 0:
            if not args.quiet:
                if args.summary_only:
                    result.print_summary()
                else:
                    result.print_summary()
                    if not args.stdout:
                        print("\n[!] PIPELINE FAILURE: Expected to find unclaimed packages but none were detected!")
            sys.exit(1)
        elif not args.quiet and not args.stdout:
            print(f"\n[✓] SUCCESS: Found {len(result.unclaimed_packages)} unclaimed packages as expected")
    elif args.fail_on_found and len(result.unclaimed_packages) > 0:
        # Normal logic: fail if unclaimed packages found
        if not args.quiet:
            if args.summary_only:
                result.print_summary()
            else:
                result.print_summary()
                if not args.stdout:
                    print("\n[!] PIPELINE FAILURE: Unclaimed packages detected!")
        sys.exit(1)

    # Output in requested format - SARIF by default, JSON with --raw
    if args.raw:
        output_data = result.to_dict()
        json_kwargs = {"indent": 4, "sort_keys": True} if args.pretty else {}
    else:
        output_data = result.to_sarif()
        # For SARIF, don't sort keys to maintain logical structure
        json_kwargs = {"indent": 4} if args.pretty else {}
    
    output_json = json.dumps(output_data, **json_kwargs)

    if args.stdout:
        # When --stdout is used, only print output
        print(output_json)
    elif not args.quiet:
        # When not using --stdout and not quiet, show summary and save to file if specified
        if args.summary_only:
            result.print_summary()
        else:
            result.print_summary()
        if args.output:
            with open(args.output, "w") as f:
                f.write(output_json)
            print(f"\n[+] Output saved to {args.output}")
    elif args.output:
        # Quiet mode but still save output file
        with open(args.output, "w") as f:
            f.write(output_json)
    
    # Exit successfully if no issues found or --fail-on-found not specified
    sys.exit(0)

if __name__ == "__main__":
    main()
