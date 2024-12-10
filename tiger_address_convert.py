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

def write_to_csv(file_name, generator, headers):
    """
    Write results from a generator to a CSV file.
    
    Parameters:
    - file_name: The CSV file to write to.
    - generator: A generator yielding rows of data (as dictionaries).
    - headers: A list of column headers for the CSV file.
    """
    with open(file_name, mode='w', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=headers)
        writer.writeheader()
        for rows in generator:
            for row in rows:
                writer.writerow(row)

def shape_to_hnr_csv(shp_filename, csv_filename):
    """
    Main feature: reads a file, writes a file
    """
    print("parsing shpfile %s" % shp_filename)
    parsed_features = parse_shp_for_geom_and_tags(shp_filename)

    i , nodelist = compile_nodelist(parsed_features)

    waylist = compile_waylist(parsed_features)

    current_file_dir = os.path.dirname(os.path.abspath(__file__))

    zip_code_file = os.path.join(current_file_dir, "zip_db.csv")
    
    print("writing %s" % csv_filename)
    fieldnames = [
        'hnr',
        'lat',
        'lon',
        'street',
        'county',
        'city',
        'state',
        'postcode',
        'zip4',
    ]

    write_to_csv(csv_filename, addressways(waylist, nodelist, i, ZipCodeLookup(zip_code_file), False), fieldnames)

if len(sys.argv) < 3:
    print("%s input.shp output.csv" % sys.argv[0])
    sys.exit()

shape_to_hnr_csv(sys.argv[1], sys.argv[2])
