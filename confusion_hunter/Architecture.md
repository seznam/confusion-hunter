# Architecture

Code is structured into components: 
- Manager
- Detectors
- Executors


## Detectors
A detector is a simple object defining what names of files are allowed or denied for what language and file types. For example we might want to detect Python's `requirements.txt` but also `requirements-dev.txt` but not `debian-requirements.txt` (debian packages). For this we defined easily extendable [schemas/](./detectors/schemas/) which are defining this behavior for us using regex expressions. 

To define and implement new schema you simply define a JSON in schemas with structure like this:

```json
{
    "language": "<language>",
    "file_types": {
        "<file_type>": {
            "allow": [
                "<regex pattern>"
            ],
            "deny": [
                "<regex pattern>"
            ]
        }
    }
}
```
Then you define new detector in [__init__.py](./detectors/__init__.py) by importing `SchemaLoader` and creating the detector:

```python
from .schema_loader import SchemaLoader

# Create new detector from schema
NewDetectorName = SchemaLoader.create_detector(os.path.join(_schemas_dir, 'new_schema_name.json'))
```

Finally you need to register it in [scanner.py](../scanner.py) by adding it to the detectors list:
```python
manager.register_detectors([
    PythonDetector,
    JavaScriptDetector,
    NewDetectorName  # Add your new detector here
])
```

## Executors

Executor is responsible for creating a list of unclaimed packages based on provided file type. Each executor gets only file type it is defined for. It parses its custom content, finds package names and then it executes utility function to check for unclaimed packages. Returns only those unclaimed.

Each executor must define:
- `supported_languages`: List of languages it handles
- `supported_file_types`: List of file types it can process
- `should_scan_file()`: Method to determine if it should process a given file
- `scan_file_async()`: Method to scan the file for unclaimed packages

Creating new Executor is quite simple. Just define it in [executors/](./executors/), it needs to extend abstract class `BaseExecutor`. Then you register it in [scanner.py](../scanner.py) by adding it to the appropriate language group:

```python
manager.register_executors_by_language("python", [
    PoetryLockExecutor(project_root),
    RequirementsExecutor(project_root),
    NewExecutorName(project_root)  # Add your new executor here
])
```

## Manager
The `ExecutionManager` class is responsible for handling the flow of scans. It uses included detectors and executors to:

1. **File Discovery**: Traverses the provided project folder using registered detectors to find supported configuration files
2. **File Scanning**: Takes all found files and runs appropriate executors based on their language and file type
3. **Result Aggregation**: Collects and returns scan results

Key methods:
- `register_detectors()`: Register file detectors
- `register_executors_by_language()`: Register executors for specific languages  
- `find_config_files()`: Discover configuration files in the project
- `scan_files()`: Execute scans on discovered files
- `run_scan()`: Complete scan workflow 


