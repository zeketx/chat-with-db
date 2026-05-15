# Application Validation Test Suite

Execute comprehensive validation tests for the Python backend and agents, returning results in a standardized JSON format for automated processing.

## Purpose

Proactively identify and fix issues in the application before they impact users or developers. By running this comprehensive test suite, you can:
- Detect syntax errors, type mismatches, and import failures
- Identify broken tests or security vulnerabilities  
- Verify dependencies and environment state
- Ensure the application is in a healthy state

## Variables

TEST_COMMAND_TIMEOUT: 5 minutes

## Instructions

- Execute each test in the sequence provided below
- Capture the result (passed/failed) and any error messages
- IMPORTANT: Return ONLY the JSON array with test results
  - IMPORTANT: Do not include any additional text, explanations, or markdown formatting
  - We'll immediately run JSON.parse() on the output, so make sure it's valid JSON
- If a test passes, omit the error field
- If a test fails, include the error message in the error field
- Execute all tests even if some fail
- Error Handling:
  - If a command returns non-zero exit code, mark as failed and immediately stop processing tests
  - Capture stderr output for error field
  - Timeout commands after `TEST_COMMAND_TIMEOUT`
  - IMPORTANT: If a test fails, stop processing tests and return the results thus far
- All file paths are relative to the project root
- Always run `pwd` and `cd` before each test to ensure you're operating in the correct directory for the given test

## Test Execution Sequence

### Backend Tests

1. **Python Syntax Check**
   - Preparation Command: None
   - Command: `find . -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" -exec python3 -m py_compile {} +`
   - test_name: "python_syntax_check"
   - test_purpose: "Validates Python syntax by compiling source files to bytecode, catching syntax errors like missing colons, invalid indentation, or malformed statements"

2. **Backend Code Quality Check**
   - Preparation Command: None
   - Command: `python3 -m pip list | grep -E "pytest|ruff|flake8|black"`
   - test_name: "backend_tooling_check"
   - test_purpose: "Checks for the presence of testing and linting tools in the current environment"

3. **All Backend Tests**
   - Preparation Command: None
   - Command: `pytest tests/ -v`
   - test_name: "all_backend_tests"
   - test_purpose: "Validates all backend functionality including database connections, agent logic, and ADW workflows"

## Report

- IMPORTANT: Return results exclusively as a JSON array based on the `Output Structure` section below.
- Sort the JSON array with failed tests (passed: false) at the top
- Include all tests in the output, both passed and failed
- The execution_command field should contain the exact command that can be run to reproduce the test
- This allows subsequent agents to quickly identify and resolve errors

### Output Structure

```json
[
  {
    "test_name": "string",
    "passed": boolean,
    "execution_command": "string",
    "test_purpose": "string",
    "error": "optional string"
  },
  ...
]
```

### Example Output

```json
[
  {
    "test_name": "all_backend_tests",
    "passed": false,
    "execution_command": "pytest tests/ -v",
    "test_purpose": "Validates all backend functionality including database connections, agent logic, and ADW workflows",
    "error": "AssertionError: Expected 200, got 500"
  },
  {
    "test_name": "python_syntax_check",
    "passed": true,
    "execution_command": "find . -name \"*.py\" -not -path \"*/venv/*\" -not -path \"*/__pycache__/*\" -exec python3 -m py_compile {} +",
    "test_purpose": "Validates Python syntax by compiling source files to bytecode"
  }
]
```
