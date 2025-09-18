# Confusion Hunter

Lightweight scanner for spotting **unclaimed dependencies** before attackers do.  

Protects your projects from **supply-chain attacks** by catching [dependency confusion](https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610) vectors by parsing your project’s manifests and scripts, then checking package names against public registries.

Built for security engineers, developers, and CI/CD environments.  
Supports `requirements.txt`, `pyproject.toml`, `package.json`, `poetry.lock`, and `uv.lock`, with more formats coming soon.  
Can also scan shell scripts, Dockerfiles, and markdown for inline install commands.

The scanner runs asynchronously, is easy to drop into pipelines, and outputs results in **SARIF** or JSON for seamless integration with your existing tooling.


## Installation
#### From PyPI

```
pip install confusion-hunter
```

#### From source
```
pip install .
python -m scanner path/to/project
```

### From Dockerfile
You can also run the scanner from Docker container:
```
docker build -t confusion-hunter .
```

## Usage
The scanner can be used in CLI, CI pipelines and in code. 

### CLI

#### Project Scanning
```
usage: confusion-hunter [-h] [--output OUTPUT] [--stdout] [--pretty] [--relative] [--raw] project_root
```

Options
- `--output` – write results to file
- `--stdout` – print to console
- `--pretty` – human-readable output
- `--relative` – relative instead of absolute paths
- `--raw` – raw JSON instead of SARIF

#### Example
```
confusion-hunter ./my-repo --pretty --stdout
```

#### Quick Package Checking

Check if specific packages are unclaimed in public registries:

```bash
# Check specific packages
hunter --unclaimed pip numpy requests non-existent-package

# Check packages from pip freeze output
pip freeze | hunter --unclaimed pip

# Check npm packages
hunter --unclaimed npm react lodash @my-org/private-package

# Get raw JSON output
hunter --unclaimed pip package1 package2 --raw --pretty --stdout
```

**Unclaimed Package Checking Options:**
- `--unclaimed {pip,npm,maven}` – Check packages against specified registry
- `packages` – Package names to check (can be combined with stdin input)

**Examples:**
```bash
# From pip freeze
pip freeze | hunter --unclaimed pip --quiet

# Check specific Python packages
hunter --unclaimed pip django flask my-internal-package

# Check NPM packages with pretty output
hunter --unclaimed npm react vue @mycompany/utils --pretty --stdout

# Save results to file
hunter --unclaimed pip package1 package2 --output results.sarif
```

### CI/CD Pipelines

The scanner is designed for easy integration into CI/CD pipelines with proper exit codes and pipeline-friendly options.

#### Quick Pipeline Setup

```bash
# Basic pipeline usage - fails if unclaimed packages found
confusion-hunter . --fail-on-found --quiet --summary-only

# With output file for security dashboards
confusion-hunter . --fail-on-found --output results.sarif

# Silent mode for scheduled scans
confusion-hunter . --fail-on-found --quiet --output scan.sarif

# Self-testing mode (for tools that contain test packages)
confusion-hunter . --expect-findings --output self-test.sarif
```

#### Pipeline Options

- `--fail-on-found` – Exit with code 1 if unclaimed packages detected
- `--expect-findings` – Invert exit logic - exit with code 1 if NO unclaimed packages found (useful for self-testing)
- `--quiet` – Suppress progress messages (errors still shown)
- `--summary-only` – Show only summary, not detailed findings
- `--output FILE` – Save results for security dashboards

#### Exit Codes

- `0` – Success (no unclaimed packages found, or expected findings found when using `--expect-findings`)
- `1` – Failure (unclaimed packages detected with `--fail-on-found`, or no findings when using `--expect-findings`)
- `2` – Error (invalid arguments, scan failure, etc.)

#### Platform Examples

**GitHub Actions**
```yaml
- name: Scan for unclaimed dependencies
  run: |
    pip install confusion-hunter
    confusion-hunter . --fail-on-found --output results.sarif
    
- name: Upload SARIF to GitHub Security
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

**GitLab CI**
```yaml
dependency_scan:
  script:
    - pip install confusion-hunter
    - confusion-hunter . --fail-on-found --output scan.sarif
  artifacts:
    reports:
      sast: scan.sarif
```

#### Using the Pipeline Script

For standardized pipeline integration, use the provided script:

```bash
# Basic usage
./scripts/pipeline-scan.sh /path/to/project

# With custom options
./scripts/pipeline-scan.sh --quiet --format json --output results.json .

# Auto-install scanner
./scripts/pipeline-scan.sh --install --verbose .
```

See `examples/` directory for complete pipeline configurations for all major CI/CD platforms.

### Python API
For programmatic usage and API details, see [Python API Documentation](./docs/python-api.md).

## Output
- Default format: SARIF JSON
- Example: [example-output.sarif.json](./examples/out/example-output.sarif.json)


## Configuration (Env Vars)

#### Debugging

- `ENABLE_LOGGING` – enable debug logs

#### Registries

- `PYPI_URL` – default: https://pypi.org/pypi

- `NPM_URL` – default: https://registry.npmjs.org

- `MAVEN_URL` – default: https://repo1.maven.org/maven2

#### Requests

- `TIMEOUT_SECS` – request timeout (default 10)

- `MAX_RETRIES` – retry attempts (default -1 = infinite)

- `BACKOFF_BASE` – exponential backoff base

- `CONN_POOL_SIZE` – aiohttp pool size (default 20)

- `REQS_PER_SECOND` – rate limit (default 10)

- `MAX_IN_FLIGHT` – max concurrent requests

## Language Support
Currently we support mainly Python and JS. There are plans to extend for Maven build configurations.

### Python
- [x] `requirements.txt`, `pyproject.toml`, `Pipfile`
- [x] lock files (`uv.lock`, `poetry.lock`)
- [x] `pip freeze` output parsing for quick package checking
- [ ] ```pip[(2-3).*] install ...``` pattern in: `*.sh`, `*Dockerfile*`, `gitlab-ci.yml`, `*.md`
- [ ] ```python[(2-3).*] -m pip install ...``` pattern in: `*.sh`, `*Dockerfile*`, `gitlab-ci.yml`, `*.md`
- [ ] conda, custom PyPi registry check

### NPM
- [x] package.json
- [x] Direct package name checking for quick verification
- [ ] .npmrc
- [ ] ```npm install ...``` pattern in: `*.sh`, `*Dockerfile*`, `gitlab-ci.yml`, `*.md`
- [ ] custom NPM registry check

### Maven
- [ ] `pom.xml`, `build.gradle`


## Development
For development setup, testing, and contribution guidelines, see [Development Documentation](./docs/development.md).