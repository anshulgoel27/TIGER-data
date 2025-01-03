
import math

from lib.zip_code_lookup import ZipCodeLookup

from .project import CoordinateTransformer
from .helpers import parse_house_number, round_point, glom_all, length, check_if_integers, interpolation_type, create_wkt_linestring


PROJCS_WKT = """GEOGCS["GCS_North_American_1983",
        DATUM["D_North_American_1983",
        SPHEROID["GRS_1980",6378137,298.257222101]],
        PRIMEM["Greenwich",0],
        UNIT["Degree",0.017453292519943295]]"""

# Sets the distance that the address ways should be from the main way, in feet.
ADDRESS_DISTANCE = 10

# Sets the distance that the ends of the address ways should be pulled back
# from the ends of the main way, in feet
ADDRESS_PULLBACK = 20


# The approximate number of feet in one degree of latitude
LAT_FEET = 364320

# Helper Functions
def interpolate_along_line(coordinates, from_hnr, to_hnr, hnr):
    """
    Interpolates latitude and longitude for a given house number along a line.
    Fallback to the centroid of the line if interpolation fails.
    """
    if from_hnr == to_hnr:
        return calculate_centroid(coordinates)

    # Handle case where to_hnr < from_hnr
    if to_hnr < from_hnr:
        from_hnr, to_hnr = to_hnr, from_hnr

    # Ensure hnr is within bounds
    if hnr < from_hnr or hnr > to_hnr:
        return calculate_centroid(coordinates)
    

    ratio = (hnr - from_hnr) / (to_hnr - from_hnr)
    total_length = sum(dist(coordinates[i], coordinates[i + 1]) for i in range(len(coordinates) - 1))
    target_length = ratio * total_length
    current_length = 0

    for i in range(len(coordinates) - 1):
        segment_length = dist(coordinates[i], coordinates[i + 1])
        if current_length + segment_length >= target_length:
            segment_ratio = (target_length - current_length) / segment_length
            lat = coordinates[i][0] + segment_ratio * (coordinates[i + 1][0] - coordinates[i][0])
            lon = coordinates[i][1] + segment_ratio * (coordinates[i + 1][1] - coordinates[i][1])
            return lat, lon
        current_length += segment_length

    return calculate_centroid(coordinates)


def should_include(hnr, interpolationtype):
    """
    Checks if a house number should be included based on interpolation type.
    """
    _, numeric_hnr, _ = parse_house_number(hnr)
    if numeric_hnr is None:
        return False

    if interpolationtype == 'all':
        return True
    if interpolationtype == 'even' and numeric_hnr % 2 == 0:
        return True
    if interpolationtype == 'odd' and numeric_hnr % 2 != 0:
        return True
    return False


def calculate_centroid(coordinates):
    """
    Calculate the centroid (geometric center) of a list of latitude and longitude points.
    """
    if not coordinates:
        raise ValueError("Coordinates list cannot be empty.")

    centroid_lat = sum(point[0] for point in coordinates) / len(coordinates)
    centroid_lon = sum(point[1] for point in coordinates) / len(coordinates)
    return centroid_lat, centroid_lon



def dist(p1, p2):
    """Calculates the distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def addressways(waylist, nodelist, first_way_id, zip_lookup: ZipCodeLookup, compile_as_ranges: bool):
    way_id = first_way_id
    distance = ADDRESS_DISTANCE
    output = []

    for tags, segments in waylist.items():
        tags = dict(tags)
        
        for segment in segments:
            lsegment = []
            rsegment = []
            lastpoint = []

            # Don't pull back the ends of very short ways too much
            seglength = length(segment, nodelist)
            if seglength < float(ADDRESS_PULLBACK) * 3.0:
                pullback = seglength / 3.0
            else:
                pullback = float(ADDRESS_PULLBACK)

            lfromadd = tags.get("tiger:lfromadd")
            ltoadd = tags.get("tiger:ltoadd")
            rfromadd = tags.get("tiger:rfromadd")
            rtoadd = tags.get("tiger:rtoadd")

            right = check_if_integers([rfromadd, rtoadd])
            left = check_if_integers([lfromadd, ltoadd])

            if not left and not right:
                continue

            # Parse house numbers once
            parsed_lfromadd = parse_house_number(lfromadd)
            parsed_ltoadd = parse_house_number(ltoadd)
            parsed_rfromadd = parse_house_number(rfromadd)
            parsed_rtoadd = parse_house_number(rtoadd)

            first = True
            firstpointid, firstpoint = nodelist[ round_point( segment[0] ) ]
            finalpointid, finalpoint = nodelist[ round_point( segment[len(segment) - 1] ) ]

            for point in segment:
                pointid, (lat, lon) = nodelist[ round_point( point ) ]

                # The approximate number of feet in one degree of longitude
                lrad = math.radians(lat)
                LON_FEET = 365527.822 * math.cos(lrad) - 306.75853 * math.cos(3 * lrad) + 0.3937 * math.cos(5 * lrad)

                # Calculate the points of the offset ways
                if lastpoint:
                    # Skip points too close to start
                    if math.sqrt((lat * LAT_FEET - firstpoint[0] * LAT_FEET)**2 + (lon * LON_FEET - firstpoint[1] * LON_FEET)**2) < pullback:
                        # Preserve very short ways (but will be rendered backwards)
                        if pointid != finalpointid:
                            continue
                    # Skip points too close to end
                    if math.sqrt((lat * LAT_FEET - finalpoint[0] * LAT_FEET)**2 + (lon * LON_FEET - finalpoint[1] * LON_FEET)**2) < pullback:
                        # Preserve very short ways (but will be rendered backwards)
                        if pointid not in (firstpointid, finalpointid):
                            continue

                    X = (lon - lastpoint[1]) * LON_FEET
                    Y = (lat - lastpoint[0]) * LAT_FEET
                    if Y != 0:
                        theta = math.pi/2 - math.atan( X / Y)
                        Xp = math.sin(theta) * distance
                        Yp = math.cos(theta) * distance
                    else:
                        Xp = 0
                        if X > 0:
                            Yp = -distance
                        else:
                            Yp = distance

                    if Y > 0:
                        Xp = -Xp
                    else:
                        Yp = -Yp

                    if first:
                        first = False
                        dX =  - (Yp * (pullback / distance)) / LON_FEET #Pull back the first point
                        dY = (Xp * (pullback / distance)) / LAT_FEET
                        if left:
                            lpoint = (lastpoint[0] + (Yp / LAT_FEET) - dY, lastpoint[1] + (Xp / LON_FEET) - dX)
                            lsegment.append( (way_id, lpoint) )
                            way_id += 1
                        if right:
                            rpoint = (lastpoint[0] - (Yp / LAT_FEET) - dY, lastpoint[1] - (Xp / LON_FEET) - dX)
                            rsegment.append( (way_id, rpoint) )
                            way_id += 1

                    else:
                        #round the curves
                        if delta[1] != 0:
                            theta = abs(math.atan(delta[0] / delta[1]))
                        else:
                            theta = math.pi / 2
                        if Xp != 0:
                            theta = theta - abs(math.atan(Yp / Xp))
                        else: theta = theta - math.pi / 2
                        r = 1 + abs(math.tan(theta/2))
                        if left:
                            lpoint = (lastpoint[0] + (Yp + delta[0]) * r / (LAT_FEET * 2), lastpoint[1] + (Xp + delta[1]) * r / (LON_FEET * 2))
                            lsegment.append( (way_id, lpoint) )
                            way_id += 1
                        if right:
                            rpoint = (lastpoint[0] - (Yp + delta[0]) * r / (LAT_FEET * 2), lastpoint[1] - (Xp + delta[1]) * r / (LON_FEET * 2))
                            rsegment.append( (way_id, rpoint) )
                            way_id += 1

                    delta = (Yp, Xp)

                lastpoint = (lat, lon)


            # Add in the last node
            dX =  - (Yp * (pullback / distance)) / LON_FEET
            dY = (Xp * (pullback / distance)) / LAT_FEET
            if left:
                lpoint = (lastpoint[0] + (Yp + delta[0]) / (LAT_FEET * 2) + dY, lastpoint[1] + (Xp + delta[1]) / (LON_FEET * 2) + dX )
                lsegment.append( (way_id, lpoint) )
                way_id += 1
            if right:
                rpoint = (lastpoint[0] - Yp / LAT_FEET + dY, lastpoint[1] - Xp / LON_FEET + dX)
                rsegment.append( (way_id, rpoint) )
                way_id += 1

            # Generate the tags for ways and nodes
            zipr = tags.get("tiger:zip_right", '')
            zipl = tags.get("tiger:zip_left", '')
            zip4r = tags.get("tiger:zip4_right", '')
            zip4l = tags.get("tiger:zip4_left", '')
            name = tags.get("name", '')

            if zipr:
                cityr = zip_lookup.get_fallback_city(zipr)
                if not cityr:
                    print(f"failed to lookup city for {tags}")
            
            if zipl:
                cityl = zip_lookup.get_fallback_city(zipl)
                if not cityl:
                    print(f"failed to lookup city for {tags}")
                
            county = tags.get("tiger:county", '')
            state = tags.get("tiger:state", '')
            id = tags.get("tiger:way_id", '')

            # Write the nodes of the offset ways
            if right:
                interpolationtype = interpolation_type(parsed_rfromadd[1], parsed_rtoadd[1])
                r_coordinates = [point[1] for point in rsegment]
                if interpolationtype:
                    if compile_as_ranges:
                        linestr = create_wkt_linestring(rsegment)
                        way = 'F' if parsed_rfromadd[1] <= parsed_rtoadd[1] else 'R'
                        lat, lon = calculate_centroid(r_coordinates)
                        output.append({
                                    "from": rfromadd,
                                    "to": rtoadd,
                                    "interpolation": interpolationtype,
                                    "lat": round(lat, 6),
                                    "lon": round(lon, 6),
                                    "street": name,
                                    "county": county,
                                    "city": cityr,
                                    "state": state,
                                    "postcode": zipr,
                                    "zip4": zip4r,
                                    "geometry": linestr,
                                    "way": way
                                })
                    else:
                        step = 1 if parsed_rfromadd[1] <= parsed_rtoadd[1] else -1
                        for hnr in range(parsed_rfromadd[1], parsed_rtoadd[1] + 1, step):
                            full_hnr = f"{parsed_rfromadd[0]}{hnr}{parsed_rfromadd[2]}".strip()
                            if should_include(full_hnr, interpolationtype):
                                lat, lon = interpolate_along_line(
                                    r_coordinates, parsed_rfromadd[1], parsed_rtoadd[1], hnr
                                )
                                yield{
                                    "hnr": full_hnr,
                                    "lat": round(lat, 6),
                                    "lon": round(lon, 6),
                                    "street": name,
                                    "county": county,
                                    "city": cityr,
                                    "state": state,
                                    "postcode": zipr,
                                    "zip4": zip4r,
                                }

            if left:
                interpolationtype = interpolation_type(parsed_lfromadd[1], parsed_ltoadd[1])
                l_coordinates = [point[1] for point in lsegment]
                if interpolationtype:
                    if compile_as_ranges:
                        linestr = create_wkt_linestring(lsegment)
                        way = 'F' if parsed_lfromadd[1] <= parsed_ltoadd[1] else 'R'
                        lat, lon = calculate_centroid(l_coordinates)
                        output.append({
                                    "from": lfromadd,
                                    "to": ltoadd,
                                    "interpolation": interpolationtype,
                                    "lat": round(lat, 6),
                                    "lon": round(lon, 6),
                                    "street": name,
                                    "county": county,
                                    "city": cityl,
                                    "state": state,
                                    "postcode": zipl,
                                    "zip4": zip4l,
                                    "geometry": linestr,
                                    "way": way
                                })
                    else:
                        step = 1 if parsed_lfromadd[1] <= parsed_ltoadd[1] else -1
                        for hnr in range(parsed_lfromadd[1], parsed_ltoadd[1] + 1):
                            full_hnr = f"{parsed_lfromadd[0]}{hnr}{parsed_lfromadd[2]}"
                            if should_include(full_hnr, interpolationtype):
                                lat, lon = interpolate_along_line(
                                    l_coordinates, parsed_lfromadd[1], parsed_ltoadd[1], hnr
                                )
                                yield{
                                    "hnr": full_hnr,
                                    "lat": round(lat, 6),
                                    "lon": round(lon, 6),
                                    "street": name,
                                    "county": county,
                                    "city": cityl,
                                    "state": state,
                                    "postcode": zipl,
                                    "zip4": zip4l,
                                }
            
    if compile_as_ranges:
        return output

def compile_nodelist(parsed_gisdata):
    nodelist = {}
    transformer = CoordinateTransformer(PROJCS_WKT)
    i = 1
    for geom, _tags in parsed_gisdata:
        for point in geom:
            r_point = round_point(point)
            if r_point not in nodelist:
                nodelist[r_point] = (i, transformer.unproject(point))
                i += 1
    transformer.destroy()
    return (i, nodelist)



def compile_waylist(parsed_gisdata):
    waylist = {}

    # Group by tiger:way_id
    for geom, tags in parsed_gisdata:
        way_key = tags.copy()
        # {'tiger:way_id': 18403490, 'name': 'Holly St', 'tiger:county': 'Perquimans', 'tiger:state': 'NC'}
        way_key = ( way_key['tiger:way_id'], tuple( [(k,v) for k,v in way_key.items()] ) )
        # (18403490, (('tiger:way_id', 18403490), ('name', 'Holly St'), ('tiger:county', 'Perquimans'), ('tiger:state', 'NC')))

        if way_key not in waylist:
            waylist[way_key] = []

        waylist[way_key].append(geom)

    ret = {}
    for (_way_id, way_key), segments in waylist.items():
        ret[way_key] = glom_all( segments )
    return ret
