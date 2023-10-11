import os
import osmium
import time

import modules.functions as functions


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


# Create an osm file that contains the map border
def run(map_, file_out):
    start_time = time.time()
    polygon = "polygons/" + map_["name"] + ".poly"

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    writer = osmium.SimpleWriter(file_out)

    # use polygon as map border
    if map_["use_polygon_shape"]:
        lon, lat = functions.poly_to_lon_lat(polygon)

    # create rectangular box as map border
    else:
        min_lat, min_lon, max_lat, max_lon = functions.min_max_lat_lon(polygon)
        lon = [min_lon, max_lon, max_lon, min_lon]  # lon_x
        lat = [max_lat, max_lat, min_lat, min_lat]  # lat_y

        # close map border - last node with same coordinates as first node
        lon.append(lon[0])
        lat.append(lat[0])

    # build and write node list
    node_id = -len(lon)
    nodes = []
    for i in range(len(lon)):
        nodes.append(node_id)
        node_id = write_node(writer, node_id, [lon[i], lat[i]])

    # only tag value "(c)www.OpenAndroMaps.org" is included in tag-mapping.
    # change tag mapping to "%s" to use arbitrary strings
    # tag_list["ele"] = "some_text_on_map_border"
    tag_list = {}
    tag_list["boundary"] = "map_inner"
    tag_list["contour_ext"] = "elevation_major"

    # write separate way for each poly segment to avoid cubic interpolation
    i = 0
    way_id = -len(nodes)
    while (i < len(nodes)-1):
        way_id = write_way(writer, way_id, nodes[i:i+2], tag_list)
        i += 1

    writer.close()

    print("    %s seconds" % round((time.time() - start_time), 1))
