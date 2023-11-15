import os
import subprocess
import time
import zipfile


# Determine a conservative number of threads to run in parallel
def get_thread_count():
    logical_cpus = os.cpu_count()
    if logical_cpus is None:
        return 1
    else:
        return max(1, int(logical_cpus*0.4))


# Returns all lon/lat coordinates from a poly file.
def poly_to_lon_lat(poly_path):
    with open(poly_path) as f:
        lon = []  # lon / x = East
        lat = []  # lat / y = North
        for line in f:
            if line[0] == " ":
                data = line.strip()
                data = " ".join(data.split())
                data = data.split()
                data = list(map(float, data))
                lon.append(data[0])
                lat.append(data[1])
    return lon, lat


# Return min_lat, min_lon and max_lat, max_lon coordinates from a
# polygon file.
def min_max_lat_lon(poly_path):
    lon, lat = poly_to_lon_lat(poly_path)
    return min(lat), min(lon), max(lat), max(lon)


def wget(source, target):
    cmd = ["wget", "-q", "--show-progress", source, "-O", target]
    subprocess.run(cmd, stdout=subprocess.PIPE, check=True)


def download_osm_source(map_, use_planet):
    if use_planet:
        src = ("https://ftp5.gwdg.de/pub/misc/openstreetmap/"
               "planet.openstreetmap.org/pbf/planet-latest.osm.pbf")
        file_out = "tmp/planet-latest.osm.pbf"
    else:
        file_out = "tmp/" + map_["name"] + ".osm.pbf"
        src = map_["source"]

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return file_out

    if not os.path.isdir("tmp"):
        os.makedirs("tmp")
    wget(src, file_out)

    return file_out


def download_auxiliary_sources():

    themes_path = "themes"
    if not os.path.isdir(themes_path):
        os.makedirs(themes_path)

    elevate = ("https://ftp.gwdg.de/pub/misc/openstreetmap/openandromaps/"
               "themes/elevate/Elevate.zip")
    elevate_target = themes_path + "/Elevate.zip"
    elevate_xml = themes_path + "/Elevate/Elevate.xml"
    if not os.path.exists(elevate_xml):
        wget(elevate, elevate_target)
        with zipfile.ZipFile(elevate_target, 'r') as zip_ref:
            zip_ref.extractall(themes_path + "/Elevate/")
        os.remove(elevate_target)
    else:
        print("    Map theme already exists.")

    tt_tm_path = "tt_tm"
    if not os.path.isdir(tt_tm_path):
        os.makedirs(tt_tm_path)

    tt = ("https://www.openandromaps.org/wp-content/snippets/makes/"
          "tt_andromaps.xml")
    tt_target = tt_tm_path + "/tt_andromaps.xml"
    if not os.path.exists(tt_target):
        wget(tt, tt_target)
    else:
        print("    Tag-transform file already exists.")

    tm_min = ("https://www.openandromaps.org/wp-content/snippets/makes/"
              "tagmapping-min.xml")
    tm_min_target = tt_tm_path + "/tagmapping-min.xml"
    if not os.path.exists(tm_min_target):
        wget(tm_min, tm_min_target)
    else:
        print("    Tag-mapping-min file already exists.")

    tm_urban = ("https://www.openandromaps.org/wp-content/snippets/makes/"
                "tagmapping-urban.xml")
    tm_urban_target = tt_tm_path + "/tagmapping-urban.xml"
    if not os.path.exists(tm_urban_target):
        wget(tm_urban, tm_urban_target)
    else:
        print("    Tag-mapping-urban file already exists.")

    pps_path = "popcat_peaks_saddles"
    if not os.path.isdir(pps_path):
        os.makedirs(pps_path)

    ti = ("https://geo.dianacht.de/topo/"
          "topographic_isolation_viefinderpanoramas.txt")
    ti_target = pps_path + "/topographic_isolation_viefinderpanoramas.txt"
    if not os.path.exists(ti_target):
        wget(ti, ti_target)
    else:
        print("    Topographic isolation file already exists.")

    sd = ("https://geo.dianacht.de/topo/"
          "saddledirection_viefinderpanoramas.100.txt")
    sd_target = pps_path + "/saddledirection_viefinderpanoramas.100.txt"
    if not os.path.exists(sd_target):
        wget(sd, sd_target)
    else:
        print("    Saddle direction file already exists.")

    popcat = ("https://ftp.gwdg.de/pub/misc/openstreetmap/openandromaps/world/"
              "PopCatFile4OAM.csv")
    popcat_target = pps_path + "/PopCatFile4OAM.csv"
    if not os.path.exists(popcat_target):
        wget(popcat, popcat_target)
    else:
        print("    Popcat file already exists.")


def extract_target_area(file_in, map_, file_out):
    start_time = time.time()
    polygon = "polygons/" + map_["name"] + ".poly"

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    # do not use "--drop-broken-refs" here, it causes problems (e.g. border
    # river in Uruguay)
    cmd = "osmconvert " + file_in + " "
    if map_["use_polygon_shape"]:
        cmd += "-B=" + polygon + " "
    else:
        min_lat, min_lon, max_lat, max_lon = min_max_lat_lon(polygon)
        box = [min_lon, min_lat, max_lon, max_lat]
        cmd += "-b=" + ",".join(str(b) for b in box) + " "
    cmd += ("--complete-multipolygons "
            "--complete-boundaries "
            "--complete-ways "
            "--hash-memory=4000 "
            "--max-objects=600000000 "
            "-o="+file_out)
    os.system(cmd)

    print("    %s seconds" % round((time.time() - start_time), 1))


def filter_data(file_in, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    # filter data and us pipe for conversion to pbf format
    cmd = ("osmfilter " + file_in + " "
           "--parameter-file=osmfilter_parameters/tags_filter_data.txt |"
           " osmconvert - --drop-version -o=" + file_out)
    os.system(cmd)

    print("    %s seconds" % round((time.time() - start_time), 1))


def merge_map_and_tt(file_list, file_out, silent):
    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    start_time = time.time()

    tt = "tt_tm/tt_andromaps.xml"
    cmd = "osmosis -q"
    for i in range(0, len(file_list)):
        if file_list[i][-3:] == "osm":
            cmd += " --rx"
        else:
            cmd += " --rbf"
        cmd += " " + file_list[i]
        if i > 0:
            cmd += " --m"
    cmd += (" --tag-transform file=" + tt + " "
            "--wb " + file_out + " omitmetadata=true")
    os.system(cmd)

    if not silent:
        print("    %s seconds" % round((time.time() - start_time), 1))


def merge_map_osmconvert(file_list, file_subtract, file_out):
    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    start_time = time.time()

    cmd = "osmconvert "
    for i, f in enumerate(file_list):
        if i > 0:
            cmd += " | osmconvert - "
        cmd += f
    cmd += (" | osmconvert - --subtract " + file_subtract + " "
            "--drop-version -o=" + file_out)
    os.system(cmd)
    print("    %s seconds" % round((time.time() - start_time), 1))


def start_mapwriter(file_in, map_, file_out):
    bbox = min_max_lat_lon("polygons/" + map_["name"] + ".poly")

    if os.path.getsize(file_in) == 0:
        print("Error: Invalid input file %s. Check previous steps for errors."
              % file_in)
        return

    cmd = ("osmosis --rb " + file_in + " "
           "--mw preferred-languages=" + map_["preferred_languages"] + " "
           "file=" + file_out + " "
           "tag-values=true "
           "tag-conf-file=" + map_["tag-mapping"] + " "
           "bbox=" + ",".join(str(b) for b in bbox) + " "
           "simplification-factor=" + str(map_["simplification-factor"]) + " "
           "zoom-interval-conf=" + map_["zoom-interval-conf"] + " "
           "threads=" + str(get_thread_count()) + " "
           "comment=\"https://github.com/marfrh/osm-map-generator\"")

    if os.path.getsize(file_in) > 300000000:
        cmd += " type=hd"
    os.system(cmd)


def remove_files(delete_set):
    for d in delete_set:
        if os.path.exists(d):
            os.remove(d)
