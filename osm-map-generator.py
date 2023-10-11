#!/usr/bin/python3

import argparse
import sys
import time

import modules.admin_relations as admin_relations
import modules.contour as contour
import modules.crags_os_open_data as crags
import modules.functions as functions
import modules.land_sea as land_sea
import modules.map_border as map_border
import modules.map_targets as map_targets
import modules.peaks_saddles as peaks_saddles
import modules.pistes as pistes
import modules.places_popcat as places_popcat
import modules.poly_nodes as poly_nodes
import modules.reduce_data as reduce_data
import modules.routes as routes


def run(map_name, result_map, use_planet, keep_temp, delete_source):
    start_t = time.time()

    map_ = map_targets.map_targets[map_name]
    tmp_files = set()

    print("\n*** Download osm source file")
    data_source = functions.download_osm_source(map_, use_planet)

    print("\n*** Download auxiliary sources (tag-transform/tag-mapping/...)")
    functions.download_auxiliary_sources()

    print("\n*** Extract area of interest")
    data_extracted = "tmp/" + map_["name"] + "_extr.o5m"
    functions.extract_target_area(data_source, map_, data_extracted)
    tmp_files.add(data_extracted)

    print("\n*** Remove unnecessary tags")
    data_filtered = "tmp/" + map_["name"] + "_extr_filt.pbf"
    functions.filter_data(data_extracted, map_, data_filtered)
    tmp_files.add(data_filtered)

    print("\n*** Create map border")
    map_border_ways = "tmp/" + map_["name"] + "_map_border.osm"
    map_border.run(map_, map_border_ways)
    tmp_files.add(map_border_ways)

    print("\n*** Resolve admin relations")
    admin_ways = "tmp/" + map_["name"] + "_admin_ways.pbf"
    admin_relations.run(data_filtered, map_, admin_ways)
    tmp_files.add(admin_ways)

    print("\n*** Create and filter polygon label nodes")
    poly_label_nodes = "tmp/" + map_["name"] + "_poly_label_nodes.pbf"
    poly_nodes.run(data_extracted, map_, poly_label_nodes)
    tmp_files.add(poly_label_nodes)

    print("\n*** Add Peak distance and saddle direction tag")
    peak_saddle_nodes = "tmp/" + map_["name"] + "_peaks_saddles.pbf"
    peaks_saddles.run(data_extracted, map_, peak_saddle_nodes)
    tmp_files.add(peak_saddle_nodes)

    print("\n*** Add popcat tag to place-nodes")
    popcat_nodes = "tmp/" + map_["name"] + "_popcat_nodes.pbf"
    places_popcat.run(data_extracted, map_, popcat_nodes)
    tmp_files.add(popcat_nodes)

    print("\n*** Split pistes from ways and resolve piste relations")
    piste_ways = "tmp/" + map_["name"] + "_pistes.pbf"
    pistes.run(data_filtered, map_, piste_ways)
    tmp_files.add(piste_ways)

    print("\n*** Merge first set of data and perform tag-transform")
    data_tag_transformed = "tmp/" + map_["name"] + "_tt.pbf"
    file_list = [poly_label_nodes, popcat_nodes, peak_saddle_nodes,
                 data_filtered]
    functions.merge_map_and_tt(file_list, data_tag_transformed, False)
    tmp_files.add(data_tag_transformed)

    print("\n*** Process routes")
    route_ways = "tmp/" + map_["name"] + "_route_ways.pbf"
    routes.run(data_tag_transformed, map_, route_ways)
    tmp_files.add(route_ways)

    print("\n*** Download and prepare contour lines")
    contour_ways = "tmp/"+map_["name"] + "_contour_ways.pbf"
    contour.run(map_, contour_ways)
    tmp_files.add(contour_ways)

    if map_["has_sea"]:
        print("\n*** Prepare land and sea")
        land_sea_polys = "tmp/" + map_["name"] + "_land_sea.pbf"
        land_sea.run(map_, land_sea_polys)
        tmp_files.add(land_sea_polys)

    if map_["has_crags"]:
        print("\n*** Prepare crags based on OS Open Data. On first run, "
              "this may take a while.")
        crag_polys = "tmp/" + map_["name"] + "_crags.pbf"
        crags.run("tmp/os_open_data/", map_, crag_polys)
        tmp_files.add(crag_polys)

    # Routes and pistes are not included in input file.
    # They are checked against the 15 tag limit in their subroutines.
    print("\n*** Reduce data for mapwriter performance and check tag limit")
    osm_ids_to_subtract = "tmp/" + map_["name"] + "_ids_to_subtract.pbf"
    tag_limit_ways = "tmp/" + map_["name"] + "_tag_limit.pbf"
    reduce_data.run(data_tag_transformed, osm_ids_to_subtract, tag_limit_ways)
    tmp_files.update([osm_ids_to_subtract, tag_limit_ways])

    # A different file sequence is necessary for osmosis / osmconvert (osmosis
    # gives priority to the first input file, osmconvert to the last input
    # file, if objects have the same osm id/no version
    print("\n*** Merge final map including contourlines and land/sea")
    data_map = "tmp/" + map_["name"] + "_data_map.pbf"
    file_list_osmconvert = [data_tag_transformed, route_ways, admin_ways,
                            piste_ways, tag_limit_ways, map_border_ways,
                            contour_ways]
    if map_["has_sea"]:
        file_list_osmconvert.append(land_sea_polys)
    if map_["has_crags"]:
        file_list_osmconvert.append(crag_polys)
    functions.merge_map_osmconvert(file_list_osmconvert, osm_ids_to_subtract,
                                   data_map)
    tmp_files.add(data_map)

    print("\n*** Apply tag mapping and produce final map")
    functions.start_mapwriter(data_map, map_, result_map)

    if not keep_temp:
        print("\n*** Remove temporary files")
        functions.remove_files(tmp_files)

    if delete_source:
        print("\n*** Delete source file")
        functions.remove_files([data_source])

    print("\n*** Finished.")
    print("    Total: %s seconds" % round((time.time() - start_t), 1))


if __name__ == "__main__":

    name = "osm-map-generator"
    descr = ("Script to create mapsforge vector maps compatible with "
             "OpenAndroMaps, based on Openstreetmap and other data sources.")
    epilog = "https://github.com/marfrh/osm-map-generator"

    p = argparse.ArgumentParser(prog=name,
                                description=descr,
                                epilog=epilog)
    p.add_argument("map_name",
                   help="Name of map to be rendered (defined in "
                   "modules/map_target.py)")
    p.add_argument("result_file",
                   help="Result map filename (.map-file)")
    p.add_argument("-p",
                   "--planet",
                   action="store_true",
                   help="Use the osm planet file hosted at gwdg as input file,"
                   "instead of the source defined in modules/map_target.py. "
                   "Download and target area extraction may take a while.")
    p.add_argument("-k",
                   "--keep_temp",
                   action="store_true",
                   help="Don't delete intermediate results (tag-transformed "
                   "data, map_border, route_ways...).")
    p.add_argument("-ds",
                   "--delete_source",
                   action="store_true",
                   help="Delete downloaded source data (default: False).")
    args = p.parse_args()

    if args.map_name not in map_targets.map_targets:
        print("Error: Could not find map target %s." % args.map_name)
        sys.exit()

    # args.result_file to map name with valid extension
    if args.result_file[-4:] == ".map":
        result_map = args.result_file
    else:
        result_map = args.result_file + ".map"

    run(args.map_name, result_map, args.planet, args.keep_temp,
        args.delete_source)
