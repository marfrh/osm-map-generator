import logging
import os
from osgeo import ogr
import osmium
import sys
import time
import zipfile

import modules.esri_shp_to_osm as shp_to_osm
import modules.functions as functions

start_rel_id = -80000000000
start_way_id = -80000000000
start_node_id = -80000000000

logger = logging.getLogger(__name__)


# convert EPSG_27700 file to WGS_84 via ogr2ogr
def EPSG_27700_to_WGS_84(file_in, file_out):
    t_srs = "WGS84"

    # British National Grid (EPSG 27700) --> maually specified
    # as automatic detection of s_srs seems to cause offset
    s_srs = ("\"+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 "
             "+x_0=400000 +y_0=-100000 +ellps=airy "
             "+towgs84=446.448,-125.157,542.060,0.1502,0.2470,"
             "0.8421,-20.4894 +units=m +no_defs\"")

    cmd = ("ogr2ogr -overwrite "
           "-t_srs " + t_srs + " -s_srs " + s_srs + " "
           + file_out + " " + file_in + " "
           ">/dev/null 2>&1")
    try:
        os.system(cmd)
    except Exception as e:
        logger.error("Error executing command: %s" % e)
        sys.exit()

# check if two ranges overlap each other
def ranges_overlap(a1, a2, b1, b2):
    if a1 <= b1 <= a2:
        return True
    elif a1 <= b2 <= a2:
        return True
    elif b1 <= a1 <= b2:
        return True
    elif b1 <= a2 <= b2:
        return True
    else:
        return False

# check if shape file overlaps with polygon bounding box
def shp_is_relevant_for_poly_bb(poly, f):
    # polygon extent
    p_min_y, p_min_x, p_max_y, p_max_x = functions.min_max_lat_lon(poly)

    # layer extent
    ogr.DontUseExceptions()
    ds = ogr.Open(f)
    layer = ds.GetLayer()
    f_min_x, f_max_x, f_min_y, f_max_y = layer.GetExtent()

    if ranges_overlap(p_min_x, p_max_x, f_min_x, f_max_x):
        if ranges_overlap(p_min_y, p_max_y, f_min_y, f_max_y):
            return True

    return False

# wrapper function to call shp to osm converson with continuous osm ids
def convert_WGS84_shp_to_osm(file_set, file_out):
    if os.path.exists(file_out):
        os.remove(file_out)
    writer = osmium.SimpleWriter(file_out)

    i_r = start_rel_id
    i_w = start_way_id
    i_n = start_node_id

    tl = {}
    tl["os_open_data"] = "crags"

    for f in file_set:
        try:
            i_w, i_n, i_r = shp_to_osm.shp_to_osm(writer, f, i_r, i_w, i_n, tl)
        except Exception as e:
            logger.error("Error processing file %s: %s" % (f, e))
            sys.exit()

    writer.close()

# Download source data and/or extract zip file if necessary. Delete
# unnecessary data.
# Convert all shp files to WGS84.
# Return one set with all files and one set with converted WGS84 files.
def download_and_convert_source_data(folder):
    src = ("https://api.os.uk/downloads/v1/products/VectorMapDistrict/"
           "downloads?area=GB&format=ESRI%C2%AE+Shapefile&redirect")
    target = folder + "vmdvec_essh_gb.zip"
    if not os.path.exists(folder + "readme.txt"):
        if not os.path.exists(target):
            try:
                functions.wget(src, target)
            except Exception as e:
                logger.error("Error downloading source data: %s" % e)
                sys.exit()

        # extract data
        with zipfile.ZipFile(target, 'r') as zip_ref:
            zip_ref.extractall(folder)

        # Delete unnecessary data
        for subdir, dirs, files in os.walk(folder + "data/"):
            for f in files:
                if f[-13:-3] != "_Ornament.":
                    os.remove(os.path.join(subdir, f))

        os.remove(target)
    else:
        logging.info("    Use existing crag source data files.")

    # Convert all shp files to WGS84, remember the converted files in a set
    file_set = set()
    file_set_WGS84 = set()
    for subdir, dirs, files in os.walk(folder + "data/"):
        for f in files:
            # convert
            if f[-13:] == "_Ornament.shp":
                file_temp = os.path.join(subdir, f)
                file_set.add(file_temp)
                f_WGS84 = file_temp[:-4] + "_WGS84.shp"
                if not os.path.exists(f_WGS84):
                    try:
                        EPSG_27700_to_WGS_84(file_temp, f_WGS84)
                    except Exception as e:
                        logger.error("Error converting file %s to WGS84: %s" % (file_temp, e))
                        sys.exit()
                file_set_WGS84.add(f_WGS84)

            # take existing file
            elif f[-19:] == "_Ornament_WGS84.shp":
                file_set_WGS84.add(os.path.join(subdir, f))

    return file_set, file_set_WGS84

def run(folder, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        logging.info("    File %s already exists." % file_out)
        return

    use_polygon_shape = map_["use_polygon_shape"]
    polygon = "polygons/" + map_["name"] + ".poly"

    if not os.path.isdir(folder):
        try:
            os.makedirs(folder)
        except Exception as e:
            logger.error("Error creating directory %s: %s" % (folder, e))
            sys.exit()

    file_set, file_set_WGS84 = download_and_convert_source_data(folder)

    # Delete unnecessary EPSG_27700 shp/dbf/prj/shx files
    for f in file_set:
        for f_type in ["shp", "dbf", "prj", "shx"]:
            f_temp = f[:-3] + f_type
            if os.path.exists(f_temp):
                try:
                    os.remove(f_temp)
                except Exception as e:
                    logger.error("Error removing file %s: %s" % (f_temp, e))
                    sys.exit()

    # Get set of shp files that are relevant for the area of interest.
    file_set_target = set()
    for shp_file in file_set_WGS84:
        if shp_is_relevant_for_poly_bb(polygon, shp_file):
            file_set_target.add(shp_file)

    # pass list of relevant files to function that calls shp_to_osm with one
    # writer and continuous osm ids
    temp_crag_data = "tmp/temp_crag_data.pbf"
    convert_WGS84_shp_to_osm(file_set_target, temp_crag_data)

    # sort crags data and cut to area of interest
    cmd = "osmosis -q --rbf " + temp_crag_data + " --s "
    if use_polygon_shape:
        cmd += "--bp file=" + polygon + " "
    else:
        min_y, min_x, max_y, max_x = functions.min_max_lat_lon(polygon)
        cmd += ("--bb" + " top=" + str(max_y) + " left=" + str(min_x) + " "
                "bottom=" + str(min_y) + " right=" + str(max_x) + " ")
    cmd += ("clipIncompleteEntities=true "
            "--wb " + file_out + " omitmetadata=true")
    try:
        os.system(cmd)
    except Exception as e:
        logger.error("Error executing command: %s" % e)
        sys.exit()

    os.remove(temp_crag_data)

    logging.info("    %s seconds" % round((time.time() - start_time), 1))
