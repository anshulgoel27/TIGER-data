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

def process_file(input_file):
    # Generate the output file name
    base_name, _ = os.path.splitext(input_file)
    output_file = f"{base_name}_streets.csv"

    street_summary = defaultdict(list)

    with open(input_file, mode='r', newline='') as infile:
        reader = csv.DictReader(infile, delimiter=';')
        
        LOG.warning("Reading Streets")
        cnt = 0
        for row in reader:
            street = row['street']
            if not street:
                continue

            street = f"{street}:{row['county']}:{row['state']}:{row['postcode']}".lower()
            if row['geometry'] == 'geometry':  # Skip header lines if present in the middle of the file
                continue

            result = re.match(r'LINESTRING\((.+)\)$', row['geometry'])
            assert result, f"Invalid geometry format: {row['geometry']}"

            points = result[1].split(',')
            street_summary[street].append([float(p) for p in points[int(len(points) / 2)].split(' ')])

            cnt += 1
            if cnt % 1000000 == 0:
                LOG.warning("Processed %s lines.", cnt)

        LOG.warning("%s lines read.", cnt)

    maxdists = [0.1, 0.3, 0.5, 0.9]
    with open(output_file, mode='w', newline='') as outfile:
        writer = csv.DictWriter(outfile, delimiter=',',
                                fieldnames=['street', 'lat', 'lon', 'county', 'state', 'postcode'],
                                lineterminator='\n')
        writer.writeheader()

        for street in sorted(street_summary):
            points = street_summary[street]
            centroid = [median(p) for p in zip(*points)]

            for mxd in maxdists:
                filtered = [p for p in points if dist(centroid, p) < mxd]
                if len(filtered) < 0.7 * len(points):
                    continue

                if len(filtered) < len(points):
                    LOG.warning("%s: Found %d outliers in %d points.", street, -len(filtered) + len(points), len(points))
                    points = filtered

                centroid = [mean(p) for p in zip(*points)]
                split = str(street).split(":")
                if len(split) == 4:
                    writer.writerow({
                        'street': split[0],
                        'lat': round(centroid[1], 6),
                        'lon': round(centroid[0], 6),
                        'county': split[1],
                        'state': split[2],
                        'postcode': split[3]
                    })
                break
            else:
                LOG.warning("%s: Dropped.", street)

    LOG.warning("Output written to %s", output_file)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process street geometries from a CSV file.")
    parser.add_argument('input_file', help="Input CSV file path")
    args = parser.parse_args()

    process_file(args.input_file)
