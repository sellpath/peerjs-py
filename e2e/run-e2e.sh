#!/bin/bash

# Store the current directory and move to the parent directory
pushd .. > /dev/null

# Add the current directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the e2e-test.py script
python e2e/e2e-test.py

# Return to the original directory
popd > /dev/null