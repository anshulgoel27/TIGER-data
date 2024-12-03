
import math
import re
from .project import unproject
from .helpers import round_point, glom_all, length, check_if_integers, interpolation_type, create_wkt_linestring


# Sets the distance that the address ways should be from the main way, in feet.
ADDRESS_DISTANCE = 30

# Sets the distance that the ends of the address ways should be pulled back
# from the ends of the main way, in feet
ADDRESS_PULLBACK = 45


# The approximate number of feet in one degree of latitude
LAT_FEET = 364613

def parse_house_number(hnr):
    """
    Parses a house number into prefix, numeric, and suffix parts.
    Examples:
      - "A10B" -> ("A", 10, "B")
      - "10B" -> ("", 10, "B")
      - "A10" -> ("A", 10, "")
      - "10" -> ("", 10, "")
    """
    match = re.match(r"^(\D*)(\d+)(\D*)$", str(hnr))
    if match:
        prefix = match.group(1)
        numeric = int(match.group(2))
        suffix = match.group(3)
        return prefix, numeric, suffix
    return None, None, None

# Helper Functions
def interpolate_along_line_with_prefix_suffix(coordinates, from_hnr, to_hnr, hnr):
    """
    Interpolates latitude and longitude for house numbers with prefix/suffix.
    """
    prefix_from, numeric_from, suffix_from = parse_house_number(from_hnr)
    prefix_to, numeric_to, suffix_to = parse_house_number(to_hnr)
    prefix_hnr, numeric_hnr, suffix_hnr = parse_house_number(hnr)

    if numeric_hnr is None or numeric_from is None or numeric_to is None:
        raise ValueError("House number interpolation requires numeric components.")

    # Ensure the prefix and suffix match for interpolation
    if prefix_from != prefix_to or suffix_from != suffix_to:
        raise ValueError("Mismatched prefixes or suffixes in house number interpolation.")

    ratio = (numeric_hnr - numeric_from) / (numeric_to - numeric_from)
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

    return coordinates[-1]  # Fallback to the last point


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


def dist(p1, p2):
    """Calculates the distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def addressways(waylist, nodelist, first_way_id):
    way_id = first_way_id
    distance = float(ADDRESS_DISTANCE)
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
            name = tags.get("name", '')
            county = tags.get("tiger:county", '')
            state = tags.get("tiger:state", '')

            # Write the nodes of the offset ways
            if right:
                # returns even, odd or all
                interpolationtype = interpolation_type(rfromadd, rtoadd, lfromadd, ltoadd)
                linestr = create_wkt_linestring(rsegment)
                r_coordinates = [point[1] for point in rsegment]
                for hnr in range(parse_house_number(rfromadd)[1], parse_house_number(rtoadd)[1] + 1):
                    full_hnr = f"{parse_house_number(rfromadd)[0]}{hnr}{parse_house_number(rfromadd)[2]}"
                    if should_include(full_hnr, interpolationtype):
                        lat, lon = interpolate_along_line_with_prefix_suffix(
                            r_coordinates, rfromadd, rtoadd, full_hnr
                        )
                        output.append({
                            'hnr': full_hnr,
                            'lat': round(lat, 6),
                            'lon': round(lon, 6),
                            'street': name,
                            'city': county,
                            'state': state,
                            'postcode': zipr,
                            'geometry': linestr
                        })

            if left:
                # returns even, odd or all
                interpolationtype = interpolation_type(lfromadd, ltoadd, rfromadd, rtoadd)
                linestr = create_wkt_linestring(lsegment)
                l_coordinates = [point[1] for point in lsegment]
                for hnr in range(parse_house_number(lfromadd)[1], parse_house_number(ltoadd)[1] + 1):
                    full_hnr = f"{parse_house_number(lfromadd)[0]}{hnr}{parse_house_number(lfromadd)[2]}"
                    if should_include(full_hnr, interpolationtype):
                        lat, lon = interpolate_along_line_with_prefix_suffix(
                            l_coordinates, lfromadd, ltoadd, full_hnr
                        )
                        output.append({
                            'hnr': full_hnr,
                            'lat': round(lat, 6),
                            'lon': round(lon, 6),
                            'street': name,
                            'city': county,
                            'state': state,
                            'postcode': zipl,
                            'geometry': linestr
                        })

    return output

def compile_nodelist(parsed_gisdata):
    nodelist = {}

    i = 1
    for geom, _tags in parsed_gisdata:
        for point in geom:
            r_point = round_point(point)
            if r_point not in nodelist:
                nodelist[r_point] = (i, unproject(point))
                i += 1

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
