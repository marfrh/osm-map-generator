import glob
import os
import time
import zipfile

import modules.esri_shp_to_osm as shp_to_osm
import modules.land_sea_grid_split as land_grid_split
import modules.functions as functions


# Replaces min/max lat/lon placeholders in template file and save
# it under result_path.
# coords: [min_lat, min_lon, max_lat, max_lon]
def insert_min_max_lat_long(template_path, result_path, coords):
    f = open(template_path, "r")
    content = f.readlines()
    f.close()

    f = open(result_path, "w")
    for line in content:
        line = line.replace("min_lat", str(coords[0]))
        line = line.replace("min_lon", str(coords[1]))
        line = line.replace("max_lat", str(coords[2]))
        line = line.replace("max_lon", str(coords[3]))
        f.write(line)
    f.close()


def run(map_, file_out):
    start_time = time.time()
    polygon = "polygons/" + map_["name"] + ".poly"

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    min_lat, min_lon, max_lat, max_lon = functions.min_max_lat_lon(polygon)

    # prepare sea file
    # adjust size by sea_marting to not have an unwanted border in the map
    sea_margin = 0.00006
    coords = [min_lat+sea_margin, min_lon+sea_margin,
              max_lat-sea_margin, max_lon-sea_margin]
    output_sea = "tmp/temp_sea.osm"
    insert_min_max_lat_long("templates/sea_template.osm", output_sea, coords)

    # download and unzip split land polygons
    land_poly = ("https://osmdata.openstreetmap.de/download/"
                 "land-polygons-split-4326.zip")
    land_poly_target = "tmp/land-polygons-split-4326.zip"
    land_poly_shp = "tmp/land-polygons-split-4326/land_polygons.shp"
    if not os.path.exists(land_poly_shp):
        functions.wget(land_poly, land_poly_target)
        with zipfile.ZipFile(land_poly_target, 'r') as zip_ref:
            zip_ref.extractall("tmp/")
        os.remove(land_poly_target)
    else:
        print("    Land polygon file already exists.")

    # cut land polygons to area of interest
    # note ogr2ogr coordinate sequence: minLon minLat maxLon maxLat
    output_land = "tmp/temp_land.shp"
    cl = [min_lon, min_lat, max_lon, max_lat]
    clipsrc = " ".join(str(c) for c in cl)
    cmd = ("ogr2ogr -overwrite -skipfailures -clipsrc " + clipsrc + " "
           + output_land + " " + land_poly_shp + " "
           ">/dev/null 2>&1")
    os.system(cmd)

    # convert land shp to osm
    temp_land = "tmp/temp_land.pbf"
    if map_["use_land_grid_split"]:
        # Use self-invented grid split function to cut large land polygons into
        # smaller overlapping polygons. This can save a small amount of
        # rendering time for large maps (e.g. 15 minutes for whole Italy with
        # processing time of around 5 minutes).
        temp_land_conv = "tmp/temp_land_conv.pbf"
        shp_to_osm.run(output_land, temp_land_conv)

        # grid split
        land_grid_split.run(temp_land_conv, temp_land)
        os.remove(temp_land_conv)
    else:
        tag_list = {}
        tag_list["layer"] = "-5"
        tag_list["natural"] = "nosea"
        shp_to_osm.run(output_land, temp_land, tag_list)

    # merge land and sea, sort land file
    cmd = ("osmosis -q --rx " + output_sea + " --s --rbf " + temp_land + " "
           "--s --m --wb " + file_out + " omitmetadata=true")
    os.system(cmd)

    # remove temporary files
    os.remove(output_sea)
    for d in glob.glob("tmp/temp_land."+"*"):
        os.remove(d)

    print("    %s seconds" % round((time.time() - start_time), 1))
