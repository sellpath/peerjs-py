import os
import pytest
import importlib.util

def get_python_files(directory):
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def test_src_directory_exists():
    assert os.path.isdir('src'), "src directory does not exist"

def test_src_contains_files():
    files = get_python_files('src')
    assert len(files) > 0, "No Python files found in src directory"

def test_python_files_are_valid():
    files = get_python_files('src')
    for file in files:
        try:
            module_name = os.path.splitext(os.path.basename(file))[0]
            spec = importlib.util.spec_from_file_location(module_name, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(f"Error in {file}: {str(e)}")

# Add more specific tests as needed