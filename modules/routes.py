import os
import time

import modules.reduce_data as reduce_data
import modules.routes_resolve_superroutes as routes_resolve_superroutes
import modules.routes_process_route_refs as routes_process_route_refs
import modules.routes_resolve_relations as routes_resolve_relations


# Route processing should occur after tag-transform. Otherwise, network-tag
# could be overwritten. Furthermore, old network tags get converted during
# tag-transform.
def run(file_in, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    temp_file_in = "tmp/temp_route_data.o5m"
    cmd = "osmconvert " + file_in + " --drop-author -o=" + temp_file_in
    os.system(cmd)

    temp_file_in_filt = "tmp/temp_route_data_filt.o5m"
    cmd = ("osmfilter " + temp_file_in + " "
           "--parameter-file=osmfilter_parameters/routes_nodes_ways.txt "
           "-o=" + temp_file_in_filt)
    os.system(cmd)

    temp_superroutes = "tmp/temp_superroutes.pbf"
    routes_resolve_superroutes.run(temp_file_in_filt, temp_superroutes)

    temp_routes_refs = "tmp/temp_route_refs.pbf"
    routes_process_route_refs.run(temp_superroutes, temp_routes_refs)

    temp_resolved_routes = "tmp/temp_resolved_routes.pbf"
    routes_resolve_relations.run(temp_routes_refs, temp_resolved_routes)

    # sort data
    temp_routes_sorted = "tmp/temp_resolved_routes_sorted.pbf"
    cmd = ("osmosis -q --rbf " + temp_resolved_routes + " --s "
           "--wb " + temp_routes_sorted + " omitmetadata=true")
    os.system(cmd)

    # check tag limit
    temp_routes_limit = "tmp/temp_routes_tags_limited.pbf"
    reduce_data.run(temp_routes_sorted, "", temp_routes_limit)

    # merge original routes and routes with limited tags (last file has
    # highest priority for osmconvert"
    cmd = ("osmconvert " + temp_routes_sorted + " "
           "| osmconvert - " + temp_routes_limit + " "
           "--drop-version -o=" + file_out)
    os.system(cmd)

    os.remove(temp_file_in)
    os.remove(temp_file_in_filt)
    os.remove(temp_superroutes)
    os.remove(temp_routes_refs)
    os.remove(temp_resolved_routes)
    os.remove(temp_routes_sorted)
    os.remove(temp_routes_limit)

    print("    %s seconds" % round((time.time() - start_time), 1))
