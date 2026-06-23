import logging
import os
import subprocess
import time
import zipfile

logger = logging.getLogger(__name__)


# Determine a conservative number of threads to run in parallel
def get_thread_count():
    logical_cpus = os.cpu_count()
    if logical_cpus is None:
        return 1
    else:
        return max(1, int(logical_cpus*0.4))


# Returns all lon/lat coordinates from a poly file.
def poly_to_lon_lat(poly_path):
    try:
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
    except Exception as e:
        logger.error(f"Error reading polygon file {poly_path}: {e}")
        raise


# Return min_lat, min_lon and max_lat, max_lon coordinates from a
# polygon file.
def min_max_lat_lon(poly_path):
    try:
        lon, lat = poly_to_lon_lat(poly_path)
        return min(lat), min(lon), max(lat), max(lon)
    except Exception as e:
        logger.error(f"Error calculating min/max lat/lon for {poly_path}: {e}")
        raise


def wget(source, target):
    try:
        cmd = ["wget", "-q", "--show-progress", source, "-O", target]
        subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"wget failed for {source}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during wget for {source}: {e}")
        raise


def download_osm_source(map_, use_planet):
    if use_planet:
        src = ("https://ftp5.gwdg.de/pub/misc/openstreetmap/"
               "planet.openstreetmap.org/pbf/planet-latest.osm.pbf")
        file_out = "tmp/planet-latest.osm.pbf"
    else:
        file_out = "tmp/" + map_["name"] + ".osm.pbf"
        src = map_["source"]

    try:
        if os.path.exists(file_out):
            logging.info("    File %s already exists." % file_out)
            return file_out

        if not os.path.isdir("tmp"):
            os.makedirs("tmp")
        
        wget(src, file_out)
        return file_out
    except Exception as e:
        logger.error(f"Error in download_osm_source: {e}")
        raise


def download_auxiliary_sources():

    themes_path = "themes"
    if not os.path.isdir(themes_path):
        try:
            os.makedirs(themes_path)
        except OSError as e:
            logger.error(f"Failed to create directory {themes_path}: {e}")
            raise

    elevate = ("https://ftp.gwdg.de/pub/misc/openstreetmap/openandromaps/"
               "themes/elevate/Elevate.zip")
    elevate_target = themes_path + "/Elevate.zip"
    elevate_xml = themes_path + "/Elevate/Elevate.xml"
    try:
        if not os.path.exists(elevate_xml):
            wget(elevate, elevate_target)
            with zipfile.ZipFile(elevate_target, 'r') as zip_ref:
                zip_ref.extractall(themes_path + "/Elevate/")
            os.remove(elevate_target)
        else:
            logging.info("    Map theme already exists.")
    except Exception as e:
        logger.error(f"Error downloading/extracting Elevate theme: {e}")
        raise

    tt_tm_path = "tt_tm"
    if not os.path.isdir(tt_tm_path):
        try:
            os.makedirs(tt_tm_path)
        except OSError as e:
            logger.error(f"Failed to create directory {tt_tm_path}: {e}")
            raise

    tt = ("https://www.openandromaps.org/wp-content/snippets/makes/"
          "tt_andromaps.xml")
    tt_target = tt_tm_path + "/tt_andromaps.xml"
    try:
        if not os.path.exists(tt_target):
            wget(tt, tt_target)
        else:
            logging.info("    Tag-transform file already exists.")
    except Exception as e:
        logger.error(f"Error downloading tag-transform file: {e}")
        raise

    tm_min = ("https://www.openandromaps.org/wp-content/snippets/makes/"
              "tagmapping-min.xml")
    tm_min_target = tt_tm_path + "/tagmapping-min.xml"
    try:
        if not os.path.exists(tm_min_target):
            wget(tm_min, tm_min_target)
        else:
            logging.info("    Tag-mapping-min file already exists.")
    except Exception as e:
        logger.error(f"Error downloading tag-mapping-min file: {e}")
        raise

    tm_urban = ("https://www.openandromaps.org/wp-content/snippets/makes/"
                "tagmapping-urban.xml")
    tm_urban_target = tt_tm_path + "/tagmapping-urban.xml"
    try:
        if not os.path.exists(tm_urban_target):
            wget(tm_urban, tm_urban_target)
        else:
            logging.info("    Tag-mapping-urban file already exists.")
    except Exception as e:
        logger.error(f"Error downloading tag-mapping-urban file: {e}")
        raise

    pps_path = "popcat_peaks_saddles"
    if not os.path.isdir(pps_path):
        try:
            os.makedirs(pps_path)
        except OSError as e:
            logger.error(f"Failed to create directory {pps_path}: {e}")
            raise

    ti = ("https://geo.dianacht.de/topo/"
          "topographic_isolation_viefinderpanoramas.txt")
    ti_target = pps_path + "/topographic_isolation_viefinderpanoramas.txt"
    try:
        if not os.path.exists(ti_target):
            wget(ti, ti_target)
        else:
            logging.info("    Topographic isolation file already exists.")
    except Exception as e:
        logger.error(f"Error downloading topographic isolation file: {e}")
        raise

    sd = ("https://geo.dianacht.de/topo/"
          "saddledirection_viefinderpanoramas.100.txt")
    sd_target = pps_path + "/saddledirection_viefinderpanoramas.100.txt"
    try:
        if not os.path.exists(sd_target):
            wget(sd, sd_target)
        else:
            logging.info("    Saddle direction file already exists.")
    except Exception as e:
        logger.error(f"Error downloading saddle direction file: {e}")
        raise

    popcat = ("https://ftp.gwdg.de/pub/misc/openstreetmap/openandromaps/world/"
              "PopCatFile4OAM.csv")
    popcat_target = pps_path + "/PopCatFile4OAM.csv"
    try:
        if not os.path.exists(popcat_target):
            wget(popcat, popcat_target)
        else:
            logging.info("    Popcat file already exists.")
    except Exception as e:
        logger.error(f"Error downloading Popcat file: {e}")
        raise


def extract_target_area(file_in, map_, file_out):
    try:
        start_time = time.time()
        polygon = "polygons/" + map_["name"] + ".poly"

        if os.path.exists(file_out):
            logging.info("    File %s already exists." % file_out)
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
        
        result = os.system(cmd)
        if result != 0:
            logger.error(f"osmconvert failed with exit code {result}")
            raise Exception("osmconvert command failed")

        logging.info("    %s seconds" % round((time.time() - start_time), 1))
    except Exception as e:
        logger.error(f"Error in extract_target_area: {e}")
        raise


def filter_data(file_in, map_, file_out):
    try:
        start_time = time.time()

        if os.path.exists(file_out):
            logging.info("    File %s already exists." % file_out)
            return

        # filter data and us pipe for conversion to pbf format
        cmd = ("osmfilter " + file_in + " "
               "--parameter-file=osmfilter_parameters/tags_filter_data.txt |"
               " osmconvert - --drop-version -o=" + file_out)
        
        result = os.system(cmd)
        if result != 0:
            logger.error(f"osmfilter/osmconvert failed with exit code {result}")
            raise Exception("osmfilter command failed")

        logging.info("    %s seconds" % round((time.time() - start_time), 1))
    except Exception as e:
        logger.error(f"Error in filter_data: {e}")
        raise


def merge_map_and_tt(file_list, file_out, silent):
    try:
        if os.path.exists(file_out):
            logging.info("    File %s already exists." % file_out)
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
        
        result = os.system(cmd)
        if result != 0:
            logger.error(f"osmosis failed with exit code {result}")
            raise Exception("osmosis command failed")

        if not silent:
            logging.info("    %s seconds" % round((time.time() - start_time), 1))
    except Exception as e:
        logger.error(f"Error in merge_map_and_tt: {e}")
        raise


def merge_map_osmconvert(file_list, file_subtract, file_out):
    try:
        if os.path.exists(file_out):
            logging.info("    File %s already exists." % file_out)
            return

        start_time = time.time()

        cmd = "osmconvert "
        for i, f in enumerate(file_list):
            if i > 0:
                cmd += " | osmconvert - "
            cmd += f
        cmd += (" | osmconvert - --subtract " + file_subtract + " "
                "--drop-version -o=" + file_out)
        
        result = os.system(cmd)
        if result != 0:
            logger.error(f"osmconvert failed with exit code {result}")
            raise Exception("osmconvert command failed")
        
        logging.info("    %s seconds" % round((time.time() - start_time), 1))
    except Exception as e:
        logger.error(f"Error in merge_map_osmconvert: {e}")
        raise


def start_mapwriter(file_in, map_, file_out):
    try:
        bbox = min_max_lat_lon("polygons/" + map_["name"] + ".poly")

        if os.path.getsize(file_in) == 0:
            logger.error("Error: Invalid input file %s. Check previous steps for errors."
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
        
        result = os.system(cmd)
        if result != 0:
            logger.error(f"osmosis mapwriter failed with exit code {result}")
            raise Exception("osmosis mapwriter command failed")
    except Exception as e:
        logger.error(f"Error in start_mapwriter: {e}")
        raise


def remove_files(delete_set):
    for d in delete_set:
        try:
            if os.path.exists(d):
                os.remove(d)
        except OSError as e:
            logger.error(f"Failed to remove file {d}: {e}")
