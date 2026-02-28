# Advanced Flow Analyzer Makefile

.PHONY: install test run clean example demo

# Default target
all: install test

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	python test_analyzer.py

# Run analysis on current project
run:
	python flow.py .. -m hybrid -o analysis_output

# Clean outputs
clean:
	rm -rf analysis_output
	rm -rf test_output_*
	rm -rf *.png
	rm -rf *.mmd
	rm -rf *.yaml
	rm -rf *.json

# Create example analysis
example:
	python flow.py .. -m reverse -o example_output
	@echo "Example analysis complete. Check example_output/"

# Demo with sample project
demo: install
	python test_analyzer.py
	@echo ""
	@echo "Demo complete! Check the test_output_* directories for results."

# Quick analysis (static only, fastest)
quick:
	python flow.py .. -m static -o quick_analysis

# Full analysis (all modes)
full:
	python flow.py .. -m hybrid -o full_analysis
	python flow.py .. -m behavioral -o behavioral_analysis
	python flow.py .. -m reverse -o reverse_analysis
	@echo "Full analysis complete!"

# Help
help:
	@echo "Available targets:"
	@echo "  install   - Install dependencies"
	@echo "  test      - Run test suite"
	@echo "  run       - Run analysis on current project"
	@echo "  clean     - Clean output files"
	@echo "  example   - Create example analysis"
	@echo "  demo      - Run full demo with tests"
	@echo "  quick     - Quick static analysis"
	@echo "  full      - Full analysis with all modes"
	@echo "  help      - Show this help"
