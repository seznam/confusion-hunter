import pytest
from npm_parser import NPMParser

# Test data
NPM_TEST_CASES = [
    (
        """
        npm install -g typescript
        npm install -g @types/node
        npm install test \\
                    test-2 \\
                    test-3 \\
                    --flag \\
                    --extra-flag = https://github.com/types/npm \\
                    # this is a comment \\
                    test-4 \\
            
        this should not be detected as an installation nor npm installer
        """,
        ["typescript", "@types/node", "test", "test-2", "test-3", "test-4"]
    ),
    (
        """
        npm install express lodash moment@^2.29
        npm install -g typescript --force
        npm install --save-dev jest eslint@latest
        """,
        ["express", "lodash", "moment", "typescript", "jest", "eslint"]
    ),
    (
        """
        npm install \\
            @scope/core@^1.2.0 \\
            @scope/utils \\
            --registry=https://npm.repo.ops.example.com/ \\
            --save-exact \\
            --no-audit \\
            # internal colour lib \\
            chalk@5
        """,
        ["@scope/core", "@scope/utils"]
    )
]

@pytest.fixture
def npm_parser():
    return NPMParser()


@pytest.mark.parametrize("command,expected", NPM_TEST_CASES)
def test_npm_parser(npm_parser, command, expected):
    """Test NPM parser with various command formats."""
    result = npm_parser.get_packages(command)
    assert result == expected, f"Expected {expected}, got {result}"


def test_npm_parser_edge_cases(npm_parser):
    """Test NPM parser with edge cases."""
    # Test empty input
    assert npm_parser.get_packages("") == []
    
    # Test input with no npm commands
    assert npm_parser.get_packages("echo 'hello'") == []
    
    # Test input with invalid npm commands
    assert npm_parser.get_packages("npm not-install package") == []

