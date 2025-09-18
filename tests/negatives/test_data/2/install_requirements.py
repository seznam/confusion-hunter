import subprocess
import sys

PYPI_HOST = "pypi.repo.ops.example.com"
PYPI_INDEX_URL = f"https://{PYPI_HOST}/simple"
EXTRA_INDEX_URL = f"https://{PYPI_HOST}/local/simple"


def install_package(package_name):
    """Installs a package from the custom PyPI repository."""
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--trusted-host", PYPI_HOST,
        # ok:dependency-confusion-pip-extra-index
        "--index-url", PYPI_INDEX_URL,
        # ok:dependency-confusion-pip-extra-index
        "--extra-index-url", EXTRA_INDEX_URL,
        package_name
    ])


def install_requirements():
    """Installs dependencies from requirements.txt using the custom PyPI repository."""
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--trusted-host", PYPI_HOST,
        # ok:dependency-confusion-pip-extra-index
        "--index-url", PYPI_INDEX_URL,
        # ok:dependency-confusion-pip-extra-index
        "--extra-index-url", EXTRA_INDEX_URL,
        "-r", "requirements.txt"
    ])


if __name__ == "__main__":
    install_requirements()
