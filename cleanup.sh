#!/bin/bash
echo "Stopping all Python processes..."
pkill -9 -f "python"
pkill -9 -f "Python"
pkill -9 -f "run_pipeline_test"
pkill -9 -f "vector_store"
pkill -9 -f "diagnose"

echo "Checking for remaining processes..."
ps aux | grep -i python | grep -v grep

echo "Cleaning up temp files..."
rm -f /tmp/*.py
rm -f /Users/mohnish/Downloads/hiring-agent/diagnose_*.py
rm -f /Users/mohnish/Downloads/hiring-agent/test_sbert.py
rm -f /Users/mohnish/Downloads/hiring-agent/test_transformers_direct.py

echo "Cleanup complete."
