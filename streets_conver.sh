#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_directory> <output_directory>"
    exit 1
fi

# Read the input and output directories from the arguments
INPUT_DIR="$1"
OUTPUT_DIR="$2"

# Ensure the output directory exists
mkdir -p "$OUTPUT_DIR"

# Loop through each CSV file in the input directory
for input_file in "$INPUT_DIR"/*.csv; do
    # Check if the input file exists and is readable
    if [ -f "$input_file" ]; then
        echo "Processing $input_file..."
        ./calculate_street_centroid.py "$input_file" "$OUTPUT_DIR"
    else
        echo "No CSV files found in $INPUT_DIR."
    fi
done

echo "Processing complete. Output files are in $OUTPUT_DIR"
