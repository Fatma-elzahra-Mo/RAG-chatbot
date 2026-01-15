#!/bin/bash

# Run API tests
echo "Running API Unit Tests..."
.venv/bin/pytest tests/unit/test_api_schemas.py -v --tb=short

echo ""
echo "Running API Integration Tests..."
.venv/bin/pytest tests/integration/test_api.py -v --tb=short -x

echo ""
echo "Test Summary:"
.venv/bin/pytest tests/unit/test_api_schemas.py tests/integration/test_api.py -v --co -q | wc -l
