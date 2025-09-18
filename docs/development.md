# Development

For testing environment we have developed pytest test cases in [tests/ folder](../tests/).
To run you need testing dependencies:

```
pip install ".[test]"
pytest tests/
```

The folder is separated into configurations that should return findings ([positives](../tests/positives/)) to test correct detection and those that should not find anything ([negatives](../tests/negatives/)) to test against known false positives.

To learn more about code structure read up on [code architecture](../confusion_hunter/Architecture.md)

## Contributing
Issues and PRs are welcome. If you hit a bug or want to extend support (e.g., new registries, new config file parsers), open a discussion.
