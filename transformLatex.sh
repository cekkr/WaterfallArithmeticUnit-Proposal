#!/bin/bash

# Fast macOS shell script to convert single $ LaTeX formulas to double $$ format
# Usage: ./latex-formula-converter.sh input.md [output.md]

set -euo pipefail

# Check if input file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <input.md> [output.md]"
    echo "If output file is not specified, changes will be made in-place"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-$INPUT_FILE}"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

# Create a temporary file for processing
TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

# Use sed to transform single $ formulas to double $$ formulas
# Pattern explanation:
# - ([^$]|^) : Match either a non-$ character or start of line
# - \$ : Match literal $
# - ([^$]+) : Match one or more non-$ characters (the formula content)
# - \$ : Match literal $
# - ([^$]|$) : Match either a non-$ character or end of line
# This prevents matching already double-$ formulas

sed -E 's/([^$]|^)\$([^$]+)\$([^$]|$)/\1$$\2$$\3/g' "$INPUT_FILE" > "$TEMP_FILE"

# Move the result to the output file
mv "$TEMP_FILE" "$OUTPUT_FILE"

if [ "$INPUT_FILE" = "$OUTPUT_FILE" ]; then
    echo "✅ Converted single $ formulas to double $$ format in '$INPUT_FILE'"
else
    echo "✅ Converted single $ formulas to double $$ format: '$INPUT_FILE' → '$OUTPUT_FILE'"
fi

# Optional: Show a summary of changes made
CHANGES=$(diff -u "$INPUT_FILE" "$OUTPUT_FILE" | grep -c "^[+-]\$\$" || true)
if [ "$CHANGES" -gt 0 ]; then
    echo "📊 Made $((CHANGES / 2)) formula conversions"
else
    echo "ℹ️  No single $ formulas found to convert"
fi
