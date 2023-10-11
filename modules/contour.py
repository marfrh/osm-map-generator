import glob
import os
import time

import modules.functions as functions


def run(map_, file_out):
    start_time = time.time()
    polygon = "polygons/" + map_["name"] + ".poly"

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
    # recommended epsilon parameter (simplify contourlines):
    # view3: 0.0001 ... 0.0005, view1: 0.00001 ... 0.0001
    cmd = "pyhgtmap "

    if map_["use_polygon_shape"]:
        cmd += "--polygon=" + polygon + " "
    else:
        min_lat, min_lon, max_lat, max_lon = functions.min_max_lat_lon(polygon)
        area = (str(min_lon) + ":" +
                str(min_lat) + ":" +
                str(max_lon) + ":" +
                str(max_lat))
        cmd += "--area=" + area + " "

    cmd += ("-s " + config["stepsize"] + " "
            "-c " + config["major_medium"] + " "
            "--srtm=" + config["srtm"] + " "
            "--source=" + config["contourline_source"] + " "
            "--pbf -o " + prefix + " "
            "--max-nodes-per-tile=0 "
            "--max-nodes-per-way=200 "
            "--start-way-id=50000000000 "
            "--start-node-id=50000000000 "
            "--write-timestamp "
            "--no-zero-contour "
            "--hgtdir=" + hgt_dir + " "
            "--simplifyContoursEpsilon=" + config["epsilon"] + " "
            ">/dev/null 2>&1")

    os.system(cmd)

    # rename for handling with osmconvert (has problems with wildcard * when
    # called from python)
    for fn in glob.glob(prefix+"*"):
        os.rename(fn, file_out)

    print("    %s seconds" % round((time.time() - start_time), 1))
