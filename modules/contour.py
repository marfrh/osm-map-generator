import glob
import os
import sys
import time

import modules.functions as functions


# Adapt corrdinates to hgt grid. Example:
# -14.1 --> -15
#  14.1 -->  14
def coord_to_int(coord):
    if coord < 0:
        return int(coord - 1)
    else:
        return int(coord)


# Get a set of hgt tile filenames which are relevant to cover the bounding
# box of polygon. Limit this set to files which are present in hgt_dir.
def get_hgt_tile_set(polygon, hgt_dir):
    min_lat, min_lon, max_lat, max_lon = functions.min_max_lat_lon(polygon)

    # adapt min/max values to hgt grid
    min_lat = coord_to_int(min_lat)
    max_lat = coord_to_int(max_lat)
    min_lon = coord_to_int(min_lon)
    max_lon = coord_to_int(max_lon)

    # [N|S]YY[W|E]XXX.hgt, with YY the latitude and XXX the longitude of the
    # lower left corner of the tile.
    x_segments = []
    for x in range(min_lon, max_lon + 1):
        if x < 0:
            x_segments.append("W" + str(abs(x)).zfill(3))
        else:
            x_segments.append("E" + str(x).zfill(3))

    y_segments = []
    for y in range(min_lat, max_lat + 1):
        if y < 0:
            y_segments.append("S" + str(abs(y)).zfill(2))
        else:
            y_segments.append("N" + str(y).zfill(2))

    poly_tile_set = set()
    for y in y_segments:
        for x in x_segments:
            poly_tile_set.add(y + x + ".hgt")

    hgt_tile_set = set()
    for subdir, dirs, files in os.walk(hgt_dir):
        for f in files:
            if f[-4:] == ".hgt":
                if f in poly_tile_set:
                    file_temp = os.path.join(subdir, f)
                    hgt_tile_set.add(file_temp)

    return hgt_tile_set


# Save a new .poly file under filename that describes the bounding box of
# polygon.
def create_bbox_area_polygon(polygon, filename):
    min_lat, min_lon, max_lat, max_lon = functions.min_max_lat_lon(polygon)

    poly_str = "TEMP\n1\n"
    poly_str += "   " + str(min_lon) + "   " + str(max_lat) + "\n"
    poly_str += "   " + str(max_lon) + "   " + str(max_lat) + "\n"
    poly_str += "   " + str(max_lon) + "   " + str(min_lat) + "\n"
    poly_str += "   " + str(min_lon) + "   " + str(min_lat) + "\n"
    poly_str += "   " + str(min_lon) + "   " + str(max_lat) + "\n"
    poly_str += "END\nEND\n"

    with open(filename, "w") as fp:
        fp.writelines(poly_str)


def run(map_, file_out):
    start_time = time.time()
    polygon = "polygons/" + map_["name"] + ".poly"

    # only needed in case of custom hgt tiles
    temp_poly = "tmp/temp_poly.poly"

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    prefix = "tmp/rc_"+map_["name"]
    hgt_dir = "tmp/hgt/"
    config = map_["contour"]

    # old version: http://katze.tfiu.de/projects/phyghtmap/phyghtmap.1.html
    # does not work with python3 because of issues:
    # https://github.com/has2k1/plotnine/issues/619
    #
    # new fork: https://github.com/agrenott/pyhgtmap
    cmd = "pyhgtmap "

    if config["contourline_source"] == "custom":

        if not map_["use_polygon_shape"]:
            create_bbox_area_polygon(polygon, temp_poly)
            polygon = temp_poly

        custom_dir = config["custom_hgt_dir"]
        if custom_dir[-1] != "/":
            custom_dir += "/"

        # Custom hgt folder can contain many files, so calling pyhgtmap with
        # *.hgt instead of specific files can be very slow. To speed up, pass a
        # specifict list of hgt files to pyhgtmap which is defined as the
        # intersecting set of the existing custom hgt files and the hgt files
        # necessary to cover the map polygon's bounding box.
        hgt_tile_set = get_hgt_tile_set(polygon, custom_dir)
        if not hgt_tile_set:
            print("Error: custom hgt tiles are missing.")
            sys.exit()

        cmd += "--polygon=" + polygon + " "

    elif map_["use_polygon_shape"]:
        cmd += "--polygon=" + polygon + " "

    else:
        min_lat, min_lon, max_lat, max_lon = functions.min_max_lat_lon(polygon)
        area = (str(min_lon) + ":" +
                str(min_lat) + ":" +
                str(max_lon) + ":" +
                str(max_lat))
        cmd += "--area=" + area + " "

    cmd += ("-s " + config["stepsize"] + " "
            "-c " + config["major_medium"] + " ")

    if config["contourline_source"] != "custom":
        cmd += "--source=" + config["contourline_source"] + " "

    cmd += ("--pbf -o " + prefix + " "
            "--max-nodes-per-tile=0 "
            "--max-nodes-per-way=200 "
            "--start-way-id=50000000000 "
            "--start-node-id=50000000000 "
            "--write-timestamp "
            "--no-zero-contour "
            "--hgtdir=" + hgt_dir + " "
            "--jobs=" + str(functions.get_thread_count()) + " "
            "--simplifyContoursEpsilon=" + config["epsilon"] + " ")

    if config["contourline_source"] == "custom":
        cmd += " ".join(hgt_tile_set) + " "

    cmd += ">/dev/null 2>&1"

    os.system(cmd)

    # rename for handling with osmconvert (has problems with wildcard * when
    # called from python)
    for fn in glob.glob(prefix+"*"):
        os.rename(fn, file_out)

    # remove temporary file, exists only in case of custom hgt tiles
    if os.path.exists(temp_poly):
        os.remove(temp_poly)

    print("    %s seconds" % round((time.time() - start_time), 1))
