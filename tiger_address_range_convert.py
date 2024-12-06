#!/usr/bin/python3

"""
Tiger road data to OSM conversion script
Creates Karlsruhe-style address ways beside the main way
based on the Massachusetts GIS script by christopher schmidt

BUGS:
- On very tight curves, a loop may be generated in the address way.
- It would be nice if the ends of the address ways were not pulled back from dead ends
"""

import os
import sys
import csv

from lib.parse import parse_shp_for_geom_and_tags
from lib.convert import addressways, compile_nodelist, compile_waylist
from lib.zip_code_lookup import ZipCodeLookup

def shape_to_range_csv(shp_filename, csv_filename):
    """
    Main feature: reads a file, writes a file
    """
    print("parsing shpfile %s" % shp_filename)
    parsed_features = parse_shp_for_geom_and_tags(shp_filename)

    i, nodelist = compile_nodelist(parsed_features)

    waylist = compile_waylist(parsed_features)

    current_file_dir = os.path.dirname(os.path.abspath(__file__))

    zip_code_file = os.path.join(current_file_dir, "zip_db.csv")

    csv_lines = addressways(waylist, nodelist, i, ZipCodeLookup(zip_code_file), True)

    print("writing %s" % csv_filename)
    fieldnames = [
        'from',
        'to',
        "interpolation",
        'lat',
        'lon',
        'street',
        'county',
        'city',
        'state',
        'postcode',
        'zip4',
        'geometry'
    ]
    with open(csv_filename, 'w', encoding="utf8") as csv_file:
        csv_writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(csv_lines)

if len(sys.argv) < 3:
    print("%s input.shp output.csv" % sys.argv[0])
    sys.exit()

shape_to_range_csv(sys.argv[1], sys.argv[2])
