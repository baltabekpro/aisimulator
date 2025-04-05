"""
Run all service tests with appropriate setup.
"""
import pytest
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if __name__ == "__main__":
    # Run all tests in the services directory
    exit_code = pytest.main(["-xvs", "services"])
    sys.exit(exit_code)
