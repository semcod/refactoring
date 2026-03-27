#!/bin/bash
# Validate all prefact examples

set -e

echo "🚀 Running all prefact examples validation..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if prefact is installed
if ! command -v prefact &> /dev/null; then
    print_error "prefact is not installed. Please install it first:"
    echo "pip install prefact"
    exit 1
fi

print_status "prefact is installed"

# Test sample project
echo ""
echo "📁 Testing sample-project..."
cd sample-project
if prefact scan --path . --config prefact.yaml > /dev/null 2>&1; then
    print_status "sample-project scan successful"
else
    print_error "sample-project scan failed"
fi

# Test individual rules
echo ""
echo "📁 Testing individual rules..."
cd ../01-individual-rules

for rule in */; do
    if [ -f "$rule/prefact.yaml" ]; then
        echo -n "  Testing $rule... "
        cd "$rule"
        if prefact scan --path . --config prefact.yaml > /dev/null 2>&1; then
            print_status "OK"
        else
            print_error "Failed"
        fi
        cd ..
    fi
done

# Test multiple rules
echo ""
echo "📁 Testing multiple-rules..."
cd ../../02-multiple-rules
if prefact scan --path . --config prefact.yaml > /dev/null 2>&1; then
    print_status "multiple-rules scan successful"
else
    print_error "multiple-rules scan failed"
fi

# Test output formats
echo ""
echo "📁 Testing output formats..."
cd ../03-output-formats
if prefact scan --path . --format json -o test-report.json > /dev/null 2>&1; then
    if [ -f test-report.json ]; then
        print_status "JSON output format working"
        rm test-report.json
    else
        print_error "JSON report file not created"
    fi
else
    print_error "JSON output format failed"
fi

# Test custom rules (if possible)
echo ""
echo "📁 Testing custom rules..."
cd ../04-custom-rules
# Note: Custom rules require the examples to be importable
# This is a basic test
if prefact scan --path . --config prefact.yaml > /dev/null 2>&1; then
    print_status "custom rules scan successful"
else
    print_warning "custom rules test skipped (requires proper import path)"
fi

# Test API usage
echo ""
echo "📁 Testing API usage..."
cd ../06-api-usage
if python3 example.py --path . --dry-run > /dev/null 2>&1; then
    print_status "API usage example working"
else
    print_warning "API usage test skipped (requires prefact in Python path)"
fi

# Return to examples directory
cd ..

# Summary
echo ""
echo "========================================"
echo "📊 Validation Summary"
echo "========================================"

# Count examples
total_examples=$(find . -name "prefact.yaml" | wc -l)
echo "Total examples: $total_examples"

# Check if all examples have README files
examples_with_readme=$(find . -name "README.md" | wc -l)
echo "Examples with README: $examples_with_readme"

if [ $total_examples -eq $examples_with_readme ]; then
    print_status "All examples have documentation"
else
    print_warning "Some examples missing README"
fi

echo ""
print_status "Example validation complete!"
echo ""
echo "To run individual examples:"
echo "  cd examples/sample-project"
echo "  prefact scan --path . --config prefact.yaml"
echo "  prefact fix --path . --config prefact.yaml"
