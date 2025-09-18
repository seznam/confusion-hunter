# Python API

Current program can be used for multi-purpose check after unclaimed packages.

You can import the module simply like this:
```python
import confusion_hunter.scanner as hunter
from pathlib import Path

project_root = Path("...")

# Quick scan
results = hunter.run_scanner(project_root)

# Advanced use
scanner = hunter.setup_scanner(project_root=project_root)
files = scanner.find_config_files()
unclaimed = scanner.scan_files(files)
```

or if you just want results:

```python
import confusion_hunter.scanner as hunter

project_source_path = Path(...)

results = hunter.run_scanner(project_source_path)
```

## Package Claim Check
```python
# Check unclaimed packages directly
packages = ["requests", "numpy", "non-existing-package"]
result = hunter.check_unclaimed_packages(packages, "pip")
print(f"Found {len(result.unclaimed_packages)} unclaimed packages")

# Or use the existing package checker
from confusion_hunter.utils.package_checker import check_packages_sync
claimed_status = check_packages_sync(packages, "pypi")
```
