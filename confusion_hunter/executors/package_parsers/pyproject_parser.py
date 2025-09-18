import re
import sys
from typing import List, Dict, Any, Set

# Try to use tomllib from standard library (Python 3.11+)
# Fall back to tomli package for earlier Python versions
try:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
except ImportError:
    tomllib = None

class PyprojectParser:
    """Simple parser for pyproject.toml files"""
    
    @staticmethod
    def get_packages(file_path: str) -> List[str]:
        """Extract package dependencies from pyproject.toml file"""
        packages = set()
        
        try:
            if tomllib:
                with open(file_path, "rb") as f:
                    data = tomllib.load(f)
                packages.update(PyprojectParser._extract_from_toml(data))
            else:
                with open(file_path, 'r') as f:
                    content = f.read()
                packages.update(PyprojectParser._extract_from_text(content))
                
        except Exception as e:
            print(f"Error reading pyproject.toml: {e}")
            
        # Remove Python itself
        packages.discard("python")
        return list(packages)
    
    @staticmethod
    def _is_pypi_dependency(req: str) -> bool:
        """Check if a requirement string refers to a PyPI package (not Git, URL, or local)"""
        if not req.strip():
            return False
            
        req_lower = req.lower()
        
        # Git URLs should not be checked on PyPI
        if any(pattern in req_lower for pattern in ['git+', 'git://', 'github.com', 'gitlab.com', '.git']):
            return False
            
        # HTTP/HTTPS URLs should not be checked on PyPI
        if req_lower.startswith(('http://', 'https://')):
            return False
            
        # Local paths should not be checked on PyPI
        if any(pattern in req for pattern in ['file://', './', '../', '/']):
            return False
            
        # SSH URLs should not be checked on PyPI
        if re.match(r'^[^@]+@[^:]+:', req):
            return False
            
        return True
    
    @staticmethod
    def _extract_package_name(req: str) -> str:
        """Extract clean package name from requirement string, only if it's a PyPI dependency"""
        if not req.strip():
            return ""
            
        # First check if this is a PyPI dependency
        if not PyprojectParser._is_pypi_dependency(req):
            return ""
            
        # Handle URLs with #egg= fragments - but we already filtered out URLs above
        if '#egg=' in req:
            req = req.split('#egg=')[1].split('&')[0]
        
        # Remove environment markers (everything after semicolon)
        if ';' in req:
            req = req.split(';')[0]
        
        # Remove version specifiers
        req = re.split(r'[<>=!~]', req)[0].strip()
        
        # Remove extras [something]
        if '[' in req:
            req = req.split('[')[0]
        
        req = req.strip().strip('"\'')
        
        # Filter out packages with invalid characters (only allow a-z, A-Z, 0-9, -, _)
        if not re.match(r'^[a-zA-Z0-9_-]+$', req):
            return ""
            
        return req
    
    @staticmethod
    def _get_local_packages(data: Dict[str, Any]) -> Set[str]:
        """Get all packages that are defined as local dependencies (not from PyPI)"""
        local_packages = set()
        
        # Check tool.uv.sources for local path dependencies
        uv_sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        for pkg_name, source_spec in uv_sources.items():
            if isinstance(source_spec, dict):
                # Check if it's a local path, git repo, or URL
                if any(key in source_spec for key in ['path', 'git', 'url', 'file']):
                    local_packages.add(pkg_name.replace('_', '-'))  # Normalize underscores to hyphens
                    local_packages.add(pkg_name.replace('-', '_'))  # Also add underscore version
        
        # Check tool.poetry.dependencies for local dependencies
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        for pkg_name, spec in poetry_deps.items():
            if pkg_name != "python" and isinstance(spec, dict):
                if any(key in spec for key in ['path', 'git', 'url', 'file']):
                    local_packages.add(pkg_name)
        
        # Check tool.poetry.dev-dependencies for local dependencies
        poetry_dev = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
        for pkg_name, spec in poetry_dev.items():
            if isinstance(spec, dict):
                if any(key in spec for key in ['path', 'git', 'url', 'file']):
                    local_packages.add(pkg_name)
        
        # Check tool.poetry.group.*.dependencies for local dependencies
        poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
        for group_name, group_data in poetry_groups.items():
            if isinstance(group_data, dict) and "dependencies" in group_data:
                for pkg_name, spec in group_data["dependencies"].items():
                    if isinstance(spec, dict):
                        if any(key in spec for key in ['path', 'git', 'url', 'file']):
                            local_packages.add(pkg_name)
        
        return local_packages
    
    @staticmethod
    def _extract_from_toml(data: Dict[str, Any]) -> Set[str]:
        """Extract packages from parsed TOML data"""
        packages = set()
        
        # First, collect all packages that are defined as local/non-PyPI sources
        local_packages = PyprojectParser._get_local_packages(data)
        
        # PEP 621 project dependencies
        project_deps = data.get("project", {}).get("dependencies", [])
        for dep in project_deps:
            pkg = PyprojectParser._extract_package_name(dep)
            if pkg and pkg not in local_packages:
                packages.add(pkg)
        
        # PEP 621 optional dependencies
        optional_deps = data.get("project", {}).get("optional-dependencies", {})
        for group_deps in optional_deps.values():
            for dep in group_deps:
                pkg = PyprojectParser._extract_package_name(dep)
                if pkg and pkg not in local_packages:
                    packages.add(pkg)
        
        # Poetry dependencies
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        for pkg_name, spec in poetry_deps.items():
            if pkg_name != "python":
                # Check if this is a URL/path dependency
                if isinstance(spec, dict):
                    # If spec is a dict, check for URL/path/git keys
                    if not any(key in spec for key in ['path', 'git', 'url', 'file']):
                        packages.add(pkg_name)
                else:
                    # If spec is a string (version spec), it's a normal dependency
                    packages.add(pkg_name)
        
        # Poetry dev dependencies
        poetry_dev = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
        for pkg_name, spec in poetry_dev.items():
            # Same logic as above for dev dependencies
            if isinstance(spec, dict):
                if not any(key in spec for key in ['path', 'git', 'url', 'file']):
                    packages.add(pkg_name)
            else:
                packages.add(pkg_name)
        
        # Poetry group dependencies (newer format)
        poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
        for group_name, group_data in poetry_groups.items():
            if isinstance(group_data, dict) and "dependencies" in group_data:
                for pkg_name, spec in group_data["dependencies"].items():
                    if isinstance(spec, dict):
                        if not any(key in spec for key in ['path', 'git', 'url', 'file']):
                            packages.add(pkg_name)
                    else:
                        packages.add(pkg_name)
        
        # Build system requires
        build_requires = data.get("build-system", {}).get("requires", [])
        for dep in build_requires:
            pkg = PyprojectParser._extract_package_name(dep)
            if pkg:
                packages.add(pkg)
        
        return packages
    
    @staticmethod
    def _extract_from_text(content: str) -> Set[str]:
        """Extract packages from raw text using regex patterns"""
        packages = set()
        
        # Simple regex patterns for fallback
        patterns = [
            r'dependencies\s*=\s*\[(.*?)\]',  # PEP 621 dependencies
            r'\[tool\.poetry\.dependencies\](.*?)(?=\[|\Z)',  # Poetry deps
            r'requires\s*=\s*\[(.*?)\]',  # Build system requires
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                # Extract quoted strings
                quoted = re.findall(r'["\']([^"\']+)["\']', match)
                for dep in quoted:
                    pkg = PyprojectParser._extract_package_name(dep)
                    if pkg:
                        packages.add(pkg)
        
        return packages
    
    @staticmethod
    def parse_pyproject_file(file_path: str) -> List[str]:
        """Alias for get_packages for backwards compatibility"""
        return PyprojectParser.get_packages(file_path)