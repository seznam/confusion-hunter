import pytest
from pip_parser import PIPParser


PIP_TEST_CASES = [
    (
        """
        pip install test \\
                    test-2 \\
                    test-3 \\
                    --flag \\
                    --extra-flag = https://github.com/types/npm \\
                    # this is a comment \\
                    test-4 \\
                    
        pip install -r requirements.txt

        pip install test-5

        pip install test-6 --extra-index-url https://github.com/types/npm
        """,
        [["test", "test-2", "test-3"], ["test-5"], ["test-6"]]
    ),
    (
        """
        pip install numpy \\
            pandas==1.5.4

        pip install -r requirements.txt

        pip install test-8

        pip3 install test-9
        """,
        [["numpy", "pandas"], ["test-8"], ["test-9"]]
    ),
    (
        """
        pip install \\
            numpy \\
            scipy \\
            pandas==1.5.4 \\
            --index-url https://pypi.repo.ops.example.com/simple \\
            --extra-index-url=https://pypi.org/simple \\
            pandas==1.5.4 \\
            --no-cache-dir
        """,
        [["numpy", "scipy", "pandas", "pandas"]]
    ),
    (
        """
        RUN     apt-get update \\
        &&  pip install -U \\
              pip \\
              pip-tools \\
              example-bootstrap \\
        &&  pip install example-execute-tests \\
        &&  pip install .
        """,
        [["pip", "pip-tools", "example-bootstrap"], ["example-execute-tests"]]
    )
]

@pytest.fixture
def pip_parser():
    return PIPParser()


@pytest.mark.parametrize("command,expected", PIP_TEST_CASES)
def test_pip_parser(pip_parser, command, expected):
    """Test PIP parser with various command formats."""
    result = pip_parser.get_packages(command)
    assert result == expected, f"Expected {expected}, got {result}"

def test_pip_parser_edge_cases(pip_parser):
    """Test PIP parser with edge cases."""
    # Test empty input
    assert pip_parser.get_packages("") == []
    
    # Test input with no pip commands
    assert pip_parser.get_packages("echo 'hello'") == []
    
    # Test input with invalid pip commands
    assert pip_parser.get_packages("pip not-install package") == [] 