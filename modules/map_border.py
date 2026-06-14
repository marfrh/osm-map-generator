import os
import osmium
import time

import modules.functions as functions
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')


def write_way(writer, i, n, tl):
    try:
        w = osmium.osm.Way("").replace(id=i, nodes=n, version=1, visible=True,
                                       changeset=1,
                                       timestamp="1970-01-01T00:59:59Z", uid=1,
                                       user="", tags=tl)
        writer.add_way(w)
        return i + 1
    except Exception as e:
        logging.error(f"Error in write_way: {e}")
        raise


def write_node(writer, i, loc, tl={}):
    try:
        n = osmium.osm.Node("").replace(id=int(i), location=loc,
                                        version=1, visible=True, changeset=1,
                                        timestamp="1970-01-01T00:59:59Z",
                                        uid=1, user="", tags=tl)
        writer.add_node(n)
        return i + 1
    except Exception as e:
        logging.error(f"Error in write_node: {e}")
        raise


def create_map_border(map_, file_out):
    polygon = "polygons/" + map_["name"] + ".poly"

    with osmium.SimpleWriter(file_out) as writer:
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


def run(map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        logging.info(f"    File {file_out} already exists.")
        return

    try:
        create_map_border(map_, file_out)
    except Exception as e:
        logging.error(f"Error in create_map_border: {e}")
    finally:
        logging.info(f"    {round((time.time() - start_time), 1)} seconds")
