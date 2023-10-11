from contextlib import contextmanager
import os
from osgeo import ogr
import osmium
import sys

start_rel_id = -10000000000
start_way_id = -10000000000
start_node_id = -10000000000


@contextmanager
def stderr_redirected(to=os.devnull):
    fd = sys.stderr.fileno()

    def _redirect_stderr(to):
        sys.stderr.close()               # + implicit flush()
        os.dup2(to.fileno(), fd)         # fd writes to 'to' file
        sys.stderr = os.fdopen(fd, 'w')  # Python writes to fd

    with os.fdopen(os.dup(fd), 'w') as old_stderr:
        with open(to, 'w') as file:
            _redirect_stderr(to=file)
        try:
            yield  # allow code to be run with the redirected stdout
        finally:
            # restore stdout.
            # buffering and flags such as CLOEXEC may be different
            _redirect_stderr(to=old_stderr)


def write_relation(writer, i, outer_ways, inner_ways, tl):
    m = []
    for w in outer_ways:
        m.append(osmium.osm.RelationMember(w, "w", "outer"))
    for w in inner_ways:
        m.append(osmium.osm.RelationMember(w, "w", "inner"))

    mp_tag = {}
    mp_tag["type"] = "multipolygon"
    rel_tl = mp_tag | tl

    r = osmium.osm.Relation("").replace(id=i, version=1, visible=True,
                                        changeset=1,
                                        timestamp="1970-01-01T00:59:59Z",
                                        uid=1, user="", tags=rel_tl, members=m)
    writer.add_relation(r)
    return i + 1


def write_way(writer, i, n, tl):
    w = osmium.osm.Way("").replace(id=i, nodes=n, version=1, visible=True,
                                   changeset=1,
                                   timestamp="1970-01-01T00:59:59Z", uid=1,
                                   user="", tags=tl)
    writer.add_way(w)
    return i + 1


def write_node(writer, i, loc, tl={}):
    n = osmium.osm.Node("").replace(id=int(i), location=loc,
                                    version=1, visible=True, changeset=1,
                                    timestamp="1970-01-01T00:59:59Z",
                                    uid=1, user="", tags=tl)
    writer.add_node(n)
    return i + 1


def process_nodes(poly, i_n, writer):
    node_ids = []

    if range(poly.GetPointCount() - 1) == 0 or poly.GetPointCount() == 0:
        return i_n, node_ids
    for i in range(poly.GetPointCount() - 1):
        node_ids.append(i_n)
        i_n = write_node(writer, i_n, [poly.GetX(i), poly.GetY(i)])
    node_ids.append(node_ids[0])
    return i_n, node_ids


# http://en.wikipedia.org/wiki/Curve_orientation
def poly_is_clockwise(poly):
    if poly.GetPointCount() < 4:
        print("error")
        return False

    # Find lowest rightmost node
    min_y = poly.GetY(0)
    i_min_y = 0
    for i in range(1, poly.GetPointCount()):
        y = poly.GetY(i)
        if y < min_y:
            min_y = y
            i_min_y = i
        elif y == min_y:
            if poly.GetX(i) > poly.GetX(i_min_y):
                min_y = y
                i_min_y = i

    # B: lowest rightmost node
    # A: node before B
    # C: node after B
    max_i = poly.GetPointCount() - 1
    B = i_min_y
    if B == 0:
        A = max_i - 1
    else:
        A = B - 1
    if B == max_i:
        C = 1
    else:
        C = B + 1

    A_x = poly.GetX(A)
    A_y = poly.GetY(A)
    B_x = poly.GetX(B)
    B_y = poly.GetY(B)
    C_x = poly.GetX(C)
    C_y = poly.GetY(C)

    area = (A_x * B_y - A_y * B_x +
            A_y * C_x - A_x * C_y +
            B_x * C_y - C_x * B_y)

    # counter clockwise
    if area > 0:
        return False
    # clockwise
    else:
        return True


# convert a land polygon shp file (WGS84) to osm format using ogr
# resulting geometries get tag list "tl"
def __shp_to_osm(writer, file_in, i_r, i_w, i_n, tl):
    ogr.DontUseExceptions()
    ds = ogr.Open(file_in)
    layer = ds.GetLayer()
    feature = layer.GetNextFeature()

    while feature:
        geometry = feature.GetGeometryRef()

        # Polygon
        if geometry.GetGeometryCount() == 1:
            way = geometry.GetGeometryRef(0)
            i_n, node_ids = process_nodes(way, i_n, writer)

            if len(node_ids) == 0:
                continue

            i_w = write_way(writer, i_w, node_ids, tl)

        # Multipolygon
        else:
            inner_ways = []
            outer_ways = []
            for g in geometry:

                # Workaround for format of land polygons: relations can be
                # MULIPOLYGONs containing POLYGONs with only one LINEARRING.
                if g.GetGeometryName() == "POLYGON":
                    geo = g.GetGeometryRef(0)
                else:
                    geo = g

                # process nodes and write way without tags
                i_n, node_ids = process_nodes(geo, i_n, writer)
                if len(node_ids) == 0:
                    continue

                # clockwise ways are outer ways
                if poly_is_clockwise(geo):
                    outer_ways.append(i_w)
                # counter-clockwise ways are inner ways
                else:
                    inner_ways.append(i_w)

                i_w = write_way(writer, i_w, node_ids, {})

            i_r = write_relation(writer, i_r, outer_ways, inner_ways, tl)

        feature = layer.GetNextFeature()

    return i_w, i_n, i_r


def shp_to_osm(writer, file_in, i_r, i_w, i_n, tl):
    # Redirect stderr to hide unnecessary error message from
    # C-level function:
    # "ERROR 1: PROJ: proj_identify: Cannot find proj.db"
    with stderr_redirected():
        return __shp_to_osm(writer, file_in, i_r, i_w, i_n, tl)


def run(file_in, file_out, tag_list={}):
    if os.path.exists(file_out):
        os.remove(file_out)
    writer = osmium.SimpleWriter(file_out)

    i_r = start_rel_id
    i_w = start_way_id
    i_n = start_node_id

    i_w, i_n, i_r = shp_to_osm(writer, file_in, i_r, i_w, i_n, tag_list)
