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

def get_tags_from_feature(po_feature, fips):
    tags = {}

    tags["tiger:way_id"] = int( po_feature.GetField("TLID") )

    if po_feature.GetField("FULLNAME"):
        tags["name"] = po_feature.GetField( "FULLNAME" )

    if fips is not None:
        county_and_state = county_fips_data.get(fips)
        if county_and_state: # e.g. 'Perquimans, NC'
            result = re.match('^(.+), ([A-Z][A-Z])', county_and_state)
            tags["tiger:county"] = result[1]
            tags["tiger:state"] = result[2]

    lfromadd = po_feature.GetField("LFROMHN")
    if lfromadd is not None:
        tags["tiger:lfromadd"] = lfromadd
    else:
        lfromadd = po_feature.GetField("LFROMADD")
        if lfromadd is not None:
            tags["tiger:lfromadd"] = lfromadd

    rfromadd = po_feature.GetField("RFROMHN")
    if rfromadd is not None:
        tags["tiger:rfromadd"] = rfromadd
    else:
        rfromadd = po_feature.GetField("RFROMADD")
        if rfromadd is not None:
            tags["tiger:rfromadd"] = rfromadd

    ltoadd = po_feature.GetField("LTOHN")
    if ltoadd is not None:
        tags["tiger:ltoadd"] = ltoadd
    else:
        ltoadd = po_feature.GetField("LTOHADD")
        if ltoadd is not None:
            tags["tiger:ltoadd"] = ltoadd

    rtoadd = po_feature.GetField("RTOHN")
    if rtoadd is not None:
        tags["tiger:rtoadd"] = rtoadd
    else:
        rtoadd = po_feature.GetField("RTOADD")
        if rtoadd is not None:
            tags["tiger:rtoadd"] = rtoadd

    zipl = po_feature.GetField("ZIPL")
    if zipl is not None:
        tags["tiger:zip_left"] = zipl

    zipr = po_feature.GetField("ZIPR")
    if zipr is not None:
        tags["tiger:zip_right"] = zipr


    zip4l = po_feature.GetField("PLUS4L")
    if zip4l is not None:
        tags["tiger:zip4_left"] = zip4l

    zip4r = po_feature.GetField("PLUS4R")
    if zip4r is not None:
        tags["tiger:zip4_right"] = zip4r

    return tags
