import os
import time

import modules.functions as functions


# Create a single node for certain polygon categories and add a bboxweight
# tag for these nodes
def run(file_in, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    # Filter relevant polygon categories
    temp_poly_data = "tmp/temp_poly_data.osm"
    cmd = ("osmfilter " + file_in + " "
           "--parameter-file=osmfilter_parameters/poly_labels.txt "
           "-o=" + temp_poly_data)
    os.system(cmd)

    # Apply tag-transform for name abbreviations and unifications
    temp_poly_data_tt = "tmp/temp_poly_data_tt.pbf"
    functions.merge_map_and_tt([temp_poly_data], temp_poly_data_tt, True)

    # Add bboxweight tags
    temp_bboxweight = "tmp/temp_bboxweight.pbf"
    cmd = ("osmconvert " + temp_poly_data_tt + " "
           "--add-bboxweight-tags "
           "-o=" + temp_bboxweight)
    os.system(cmd)

    # Convert to nodes
    # info: cannot apply --complete-multipolygons when reading standard input,
    # therefore separate execution of osmconvert
    poly_nodes = "tmp/temp_poly_nodes.pbf"
    cmd = ("osmconvert " + temp_bboxweight + " "
           "--all-to-nodes "
           "--object-type-offset=100000000000+1 "
           "--max-objects=200000000 "
           "--complete-multipolygons "
           "--drop-broken-refs "
           "-o=" + poly_nodes)
    os.system(cmd)

    # Filter building relations
    temp_building_relations = "tmp/temp_building_relations.o5m"
    cmd = ("osmfilter " + file_in + " "
           "--parameter-file="
           "osmfilter_parameters/building_relations_step_1.txt "
           "-o=" + temp_building_relations)
    os.system(cmd)

    # Convert building-multipolygon-relationens (with house number) to a node
    # with house number
    temp_building_nodes = "tmp/temp_building_relation_nodes.o5m"
    cmd = ("osmconvert " + temp_building_relations + " "
           "--all-to-nodes "
           "--object-type-offset=200000000000+1 "
           "--max-objects=200000000 "
           "--complete-multipolygons "
           "--drop-broken-refs "
           "-o=" + temp_building_nodes)
    os.system(cmd)

    # Only keep nodes
    building_nodes_filt = "tmp/temp_building_nodes_filt.osm"
    cmd = ("osmfilter " + temp_building_nodes + " "
           "--parameter-file="
           "osmfilter_parameters/building_relations_step_2.txt "
           "-o=" + building_nodes_filt)
    os.system(cmd)

    # Merge node categories
    cmd = ("osmconvert " + poly_nodes + " " + building_nodes_filt + " "
           "| osmconvert - " + temp_bboxweight + " "
           "--drop-version -o=" + file_out)
    os.system(cmd)

    os.remove(temp_poly_data)
    os.remove(temp_poly_data_tt)
    os.remove(poly_nodes)
    os.remove(temp_building_relations)
    os.remove(temp_building_nodes)
    os.remove(building_nodes_filt)
    os.remove(temp_bboxweight)

    print("    %s seconds" % round((time.time() - start_time), 1))
