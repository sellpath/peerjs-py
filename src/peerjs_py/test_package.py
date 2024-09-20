import os
import pytest
import importlib.util

def get_python_files(directory):
    return [os.path.join(root, file)
            for root, _, files in os.walk(directory)
            for file in files if file.endswith('.py')]

@pytest.fixture
def src_directory():
    return 'src'

def test_src_directory_exists(src_directory):
    assert os.path.isdir(src_directory), f"{src_directory} directory does not exist"

def test_src_contains_files(src_directory):
    files = get_python_files(src_directory)
    assert files, f"No Python files found in {src_directory} directory"

@pytest.mark.parametrize('file', get_python_files('src'))
def test_python_file_is_valid(file):
    try:
        module_name = os.path.splitext(os.path.basename(file))[0]
        spec = importlib.util.spec_from_file_location(module_name, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        pytest.fail(f"Error in {file}: {str(e)}")