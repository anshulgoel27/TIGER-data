"""
Parse ESRI Shapefile and extract geometries and tags (key-value pairs)
"""

import os.path
import json
import re

try:
    from osgeo import ogr
except ImportError:
    import ogr

# https://www.census.gov/geo/reference/codes/cou.html
# tiger_county_fips.json was generated from the following:
# wget https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt
# cat national_county.txt | \
# perl -F, -naE'($F[0] ne 'AS') && $F[3] =~ s/ ((city|City|County|District|Borough|City and Borough|
# Municipio|Municipality|Parish|Island|Census Area)(?:, |\Z))+//;
# say qq(  "$F[1]$F[2]": "$F[3], $F[0]",)'

with open(os.path.dirname(__file__) + "/../tiger_county_fips.json", encoding="utf8") as json_file:
    county_fips_data = json.load(json_file)

def extract_fips_code(filename):
    """
    Extract the 5-digit FIPS code from the file name.

    Args:
        filename (str): The file name to process.

    Returns:
        str: The extracted FIPS code, or None if no match is found.
    """
    regex = r"tl_\d{4}_(\d{5})_(addrfeat|edges)\.shp"
    match = re.search(regex, filename)
    if match:
        return match.group(1)  # Return the captured FIPS code
    return None  # No match found

def parse_shp_for_geom_and_tags(filename):
    # ogr.RegisterAll()

    ogr_driver = ogr.GetDriverByName("ESRI Shapefile")
    po_ds = ogr_driver.Open(filename)

    if po_ds is None:
        raise "Open failed."

    po_layer = po_ds.GetLayer(0)

    # fieldnames = []
    # layer_definition = po_layer.GetLayerDefn()
    # for i in range(layer_definition.GetFieldCount()):
    #     fieldnames.append(layer_definition.GetFieldDefn(i).GetName())
    # sys.stderr.write(",".join(fieldnames))

    po_layer.ResetReading()

    ret = []

    fips = extract_fips_code(filename)
    if fips is None:
        print("Fips None for file {}", filename)
        return ret
    
    po_feature = po_layer.GetNextFeature()
    while po_feature:
        tags = get_tags_from_feature(po_feature, fips)
        geom = get_geometry_from_feature(po_feature)

        ret.append( (geom, tags) )

        po_feature = po_layer.GetNextFeature()

    return ret

def get_geometry_from_feature(po_feature):
    geom = []
    rawgeom = po_feature.GetGeometryRef()
    for i in range( rawgeom.GetPointCount() ):
        geom.append( (rawgeom.GetX(i), rawgeom.GetY(i)) )
    return geom


def get_field_if_exists(feature, field_name):
    """
    Check if a field exists in an OGR feature and return its value if it does.

    :param feature: OGR Feature object
    :param field_name: Name of the field to check
    :return: The field value if it exists, or None if the field does not exist
    """
    if feature.GetFieldIndex(field_name) != -1:
        return feature.GetField(field_name)
    return None

def get_tags_from_feature(po_feature, fips):
    """
    Extract tags from a given feature and optional FIPS code.

    :param po_feature: OGR Feature object
    :param fips: FIPS code as a string
    :return: Dictionary of tags
    """
    tags = {}

    # Mandatory tag
    tags["tiger:way_id"] = int(get_field_if_exists(po_feature, "TLID"))

    # Optional name tag
    fullname = get_field_if_exists(po_feature, "FULLNAME")
    if fullname:
        tags["name"] = fullname

    # FIPS-based county and state
    if fips:
        county_and_state = county_fips_data.get(fips)
        if county_and_state:  # Example: 'Perquimans, NC'
            result = re.match(r'^(.+), ([A-Z]{2})$', county_and_state)
            if result:
                tags["tiger:county"] = result.group(1)
                tags["tiger:state"] = result.group(2)

    # Address fields with fallback
    address_fields = [
        ("LFROMHN", "LFROMADD", "tiger:lfromadd"),
        ("RFROMHN", "RFROMADD", "tiger:rfromadd"),
        ("LTOHN", "LTOADD", "tiger:ltoadd"),
        ("RTOHN", "RTOADD", "tiger:rtoadd"),
    ]
    for primary, fallback, tag_name in address_fields:
        value = get_field_if_exists(po_feature, primary) or get_field_if_exists(po_feature, fallback)
        if value is not None:
            tags[tag_name] = value

    # ZIP fields
    zip_fields = {
        "ZIPL": "tiger:zip_left",
        "ZIPR": "tiger:zip_right",
        "PLUS4L": "tiger:zip4_left",
        "PLUS4R": "tiger:zip4_right",
    }
    for field, tag_name in zip_fields.items():
        value = get_field_if_exists(po_feature, field)
        if value is not None:
            tags[tag_name] = value

    

    return tags

