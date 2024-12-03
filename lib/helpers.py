import math
import re

def parse_house_number(hnr):
    """
    Parses a house number into prefix, numeric, and suffix parts.
    Examples:
      - "A10B" -> ("A", 10, "B")
      - "10B" -> ("", 10, "B")
      - "A10" -> ("A", 10, "")
      - "10" -> ("", 10, "")
    """
    match = re.match(r"^(\D*)(\d+)(\D*)$", str(hnr).strip())
    if match:
        prefix = match.group(1)
        numeric = int(match.group(2))
        suffix = match.group(3)
        return prefix, numeric, suffix
    return None, None, None


def round_point( point, accuracy=8 ):
    """
    Rounds all numbers in a list of coordinates
    """
    return (round(point[0], accuracy), round(point[1], accuracy))

def adjacent( left, right ):
    """
    Returns true if two segments are connected at their beginnings or ends
    """

    left_left = round_point(left[0])
    left_right = round_point(left[-1])
    right_left = round_point(right[0])
    right_right = round_point(right[-1])

    return ( left_left == right_left or
             left_left == right_right or
             left_right == right_left or
             left_right == right_right )

def glom( left, right ):
    """
    Returns the combination of two segments. Might reverse one or the other
    to match the adjacent point of both.
    """

    left = list( left )
    right = list( right )

    left_left = round_point(left[0])
    left_right = round_point(left[-1])
    right_left = round_point(right[0])
    right_right = round_point(right[-1])

    if left_left == right_left:
        left.reverse()
        return left[0:-1] + right

    if left_left == right_right:
        return right[0:-1] + left

    if left_right == right_left:
        return left[0:-1] + right

    if left_right == right_right:
        right.reverse()
        return left[0:-1] + right

    raise 'segments are not adjacent'

def glom_once( segments ):
    """
    Takes a list of segments, looks at the last and tries to find an adjacent
    segment in the remaining. If found combines them.
    Returns a list of (now combined) segments and a list of still uncombined
    segments.
    """
    if len(segments)==0:
        return segments

    unsorted = list( segments )
    x = unsorted.pop(0)

    while len( unsorted ) > 0:
        n = len( unsorted )

        for i in range(0, n):
            y = unsorted[i]
            if adjacent( x, y ):
                y = unsorted.pop(i)
                x = glom( x, y )
                break

        # Sorted and unsorted lists have no adjacent segments
        if len( unsorted ) == n:
            break

    return x, unsorted

def glom_all( segments ):
    """
    Takes a list of segments and combines as many as possible together. Returns
    a list of (now combined) segments.
    """
    unsorted = segments
    chunks = []

    while unsorted != []:
        chunk, unsorted = glom_once( unsorted )
        chunks.append( chunk )

    return chunks


def length(segment, nodelist):
    '''Returns the length (in feet) of a segment'''
    first = True
    distance = 0
    lat_feet = 364613  # The approximate number of feet in one degree of latitude
    for point in segment:
        _pointid, (lat, lon) = nodelist[ round_point( point ) ]
        if first:
            first = False
        else:
            # The approximate number of feet in one degree of longitude
            lrad = math.radians(lat)
            lon_feet = 365527.822 * math.cos(lrad) \
                       - 306.75853 * math.cos(3 * lrad) \
                       + 0.3937 * math.cos(5 * lrad)
            distance += math.sqrt(
                            ((lat - previous[0])*lat_feet)**2 \
                            + ((lon - previous[1])*lon_feet)**2
                        )
        previous = (lat, lon)
    return distance


def check_if_integers(numbers):
    """
    Returns true if all members of lists are integers.
    """
    for number in numbers:
        if not number:
            return False
        try:
            _, hnr, _ = parse_house_number(number)
            int(hnr)
        except ValueError:
            print("Non integer address: %s" % number)
            return False

    return True

def interpolation_type(this_from, this_to, other_from, other_to):
    """
    Check road side (e.g. left) and other side (right) if number range is 'even'
    or 'odd'. If in doubt 'all'.
    """
    if this_from is None or this_to is None:
        return None

    if other_from is not None and other_to is not None:
        if (int(this_from) % 2) == 0 and (int(this_to) % 2) == 0:
            if (int(other_from) % 2) == 1 and (int(other_to) % 2) == 1:
                return "even"

        elif (int(this_from) % 2) == 1 and (int(this_to) % 2) == 1:
            if (int(other_from) % 2) == 0 and (int(other_to) % 2) == 0:
                return "odd"

    return "all"

def create_wkt_linestring(segment):
    """
    Create well known text LINESTRING()
    """
    coord_pairs = []
    for _i, point in segment:
        coord_pairs.append( "%f %f" % (point[1], point[0]) )
    return 'LINESTRING(' + ','.join(coord_pairs) + ')'
