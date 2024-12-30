#!/usr/bin/env python3

from collections import defaultdict
from statistics import mean, median
from math import sqrt
import csv
import re
import logging
import os

LOG = logging.getLogger()
LOG.setLevel(logging.WARNING)

def dist(p1, p2):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def process_file(input_file, output_dir):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate the output file name
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}_postals.csv")

    postal_summary = defaultdict(list)

    with open(input_file, mode='r', newline='') as infile:
        reader = csv.DictReader(infile, delimiter=';')
        
        LOG.warning("Reading postcodes")
        cnt = 0
        for row in reader:
            postcode = row['postcode']
            if not postcode:
                continue

            # In rare cases the postcode might be empty
            if not re.match(r'^\d\d\d\d\d$', postcode):
                continue

            postcode = f"{row['city']}:{row['county']}:{row['state']}:{postcode}".lower()
            if row['geometry'] == 'geometry':  # Skip header lines if present in the middle of the file
                continue

            result = re.match(r'LINESTRING\((.+)\)$', row['geometry'])
            assert result, f"Invalid geometry format: {row['geometry']}"

            points = result[1].split(',')
            postal_summary[postcode].append([float(p) for p in points[int(len(points) / 2)].split(' ')])

            cnt += 1
            if cnt % 1000000 == 0:
                LOG.warning("Processed %s lines.", cnt)

        LOG.warning("%s lines read.", cnt)

    maxdists = [0.1, 0.3, 0.5, 0.9]
    with open(output_file, mode='w', newline='') as outfile:
        writer = csv.DictWriter(outfile, delimiter=',',
                                fieldnames=['postcode', 'city', 'county', 'state', 'lat', 'lon'],
                                lineterminator='\n')
        writer.writeheader()

        for postcode in sorted(postal_summary):
            points = postal_summary[postcode]
            centroid = [median(p) for p in zip(*points)]

            for mxd in maxdists:
                filtered = [p for p in points if dist(centroid, p) < mxd]
                if len(filtered) < 0.7 * len(points):
                    continue

                if len(filtered) < len(points):
                    LOG.warning("%s: Found %d outliers in %d points.", postcode, -len(filtered) + len(points), len(points))
                    points = filtered

                centroid = [mean(p) for p in zip(*points)]
                split = str(postcode).split(":")
                if len(split) == 3:
                    writer.writerow({
                        'postcode': split[3],
                        'city': split[0],
                        'county': split[1],
                        'state': split[2],
                        'lat': round(centroid[1], 6),
                        'lon': round(centroid[0], 6)
                    })
                break
            else:
                LOG.warning("%s: Dropped.", postcode)

    LOG.warning("Output written to %s", output_file)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process street geometries from a CSV file.")
    parser.add_argument('input_file', help="Input CSV file path")
    parser.add_argument('output_dir', help="Output directory path")
    args = parser.parse_args()

    process_file(args.input_file, args.output_dir)
