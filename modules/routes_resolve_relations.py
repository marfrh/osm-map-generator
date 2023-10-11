import os
import osmium
import math

# if set to True, ways for mtb and cycle routes are copys of the
# original way with net id.
split_mtb_cycle_ways = True

# in source data, cy/mtb/chw share the same network-tag
network_sets = {
    "hk": {"iwn", "nwn", "rwn", "lwn"},
    "cy": {"icn", "ncn", "rcn", "lcn"},
    "mtb": {"icn", "ncn", "rcn", "lcn"},
    }

route_sets = {
    "hk": {"iwn", "nwn", "rwn", "lwn"},
    "cy": {"bicycle"},
    "mtb": {"mtb"},
    }

osmc_color = {"black", "whiteyellow", "red", "green", "blue", "brown",
              "orange", "gray", "purple"}
osmc_fg = {"ammonit", "bridleway", "heart", "hiker", "mine", "shell",
           "shell_modern", "tower", "black_arch", "black_backslash",
           "black_bar", "black_circle", "black_corner", "black_crest",
           "black_cross", "black_diamond", "black_diamond_line", "black_dot",
           "black_fork", "black_hiker", "black_horse", "black_lower",
           "black_pointer", "black_rectangle", "black_rectangle_line",
           "black_red_diamond", "black_stripe", "black_triangle",
           "black_triangle_line", "black_turned_t", "black_x", "blue_arch",
           "blue_backslash", "blue_bar", "blue_bowl", "blue_circle",
           "blue_corner", "blue_cross", "blue_diamond", "blue_dot",
           "blue_fork", "blue_hiker", "blue_l", "blue_lower", "blue_pointer",
           "blue_rectangle", "blue_right", "blue_slash", "blue_stripe",
           "blue_triangle", "blue_triangle_line", "blue_triangle_turned",
           "blue_turned_t", "blue_x", "brown_bar", "brown_diamond",
           "brown_dot", "brown_hiker", "brown_lower", "brown_pointer",
           "brown_rectangle", "brown_stripe", "brown_x", "gray_bar",
           "gray_pointer", "gray_triangle", "green_arch", "green_backslash",
           "green_bar", "green_bowl", "green_circle", "green_corner",
           "green_cross", "green_diamond", "green_diamond_line", "green_dot",
           "green_drop_line", "green_fork", "green_hiker", "green_horse",
           "green_l", "green_lower", "green_pointer", "green_rectangle",
           "green_right", "green_slash", "green_stripe", "green_triangle",
           "green_triangle_line", "green_triangle_turned", "green_turned_t",
           "green_wheel", "green_x", "orange_bar", "orange_circle",
           "orange_cross", "orange_diamond", "orange_diamond_line",
           "orange_dot", "orange_hexagon", "orange_hiker", "orange_lower",
           "orange_pointer", "orange_rectangle", "orange_right",
           "orange_stripe", "orange_triangle", "purple_bar", "purple_circle",
           "purple_diamond", "purple_dot", "purple_lower", "purple_pointer",
           "purple_rectangle", "purple_stripe", "purple_triangle", "red_arch",
           "red_backslash", "red_bar", "red_circle", "red_corner", "red_crest",
           "red_cross", "red_diamond", "red_diamond_line", "red_dot",
           "red_drop", "red_drop_line", "red_fork", "red_hiker", "red_l",
           "red_lower", "red_pointer", "red_rectangle", "red_right",
           "red_shell", "red_slash", "red_stripe", "red_triangle",
           "red_triangle_line", "red_triangle_turned", "red_turned_t",
           "red_wheel", "red_x", "white_arch", "white_backslash", "white_bar",
           "white_circle", "white_corner", "white_cross", "white_diamond",
           "white_diamond_line", "white_dot", "white_hiker", "white_lower",
           "white_pointer", "white_rectangle", "white_rectangle_line",
           "white_red_diamond", "white_right", "white_slash", "white_stripe",
           "white_triangle", "white_triangle_line", "white_triangle_turned",
           "white_turned_t", "white_x", "wolfshook", "yellow_arch",
           "yellow_backslash", "yellow_bar", "yellow_bowl", "yellow_circle",
           "yellow_corner", "yellow_cross", "yellow_diamond",
           "yellow_diamond_line", "yellow_dot", "yellow_fork",
           "yellow_hexagon", "yellow_hiker", "yellow_l", "yellow_lower",
           "yellow_pointer", "yellow_rectangle", "yellow_rectangle_line",
           "yellow_shell", "yellow_slash", "yellow_stripe", "yellow_triangle",
           "yellow_triangle_line", "yellow_triangle_turned", "yellow_turned_t",
           "yellow_x"}
osmc_bg = {"black", "black_circle", "black_frame", "black_round", "white",
           "white_circle", "white_frame", "white_round", "yellow",
           "yellow_circle", "yellow_frame", "yellow_round", "red",
           "red_circle", "red_frame", "red_round", "green", "green_circle",
           "green_frame", "green_round", "blue", "blue_circle", "blue_frame",
           "blue_round", "brown", "brown_circle", "brown_frame", "brown_round",
           "orange", "orange_circle", "orange_frame", "orange_round", "gray",
           "gray_circle", "gray_frame", "gray_round", "purple",
           "purple_circle", "purple_frame", "purple_round"}
osmc_tc = {"black", "white", "yellow", "red", "green", "blue", "brown",
           "orange", "gray", "purple"}


# return integer network priority corresponding to osm network tag value
def network_priority(network):
    priority_hike = {"iwn": 4, "nwn": 3, "rwn": 2, "lwn": 1, "own": 0,
                     "pwn": 0, "": 0}
    priority_cycle = {"icn": 4, "ncn": 3, "rcn": 2, "lcn": 1, "ocn": 0,
                      "pcn": 0, "": 0}
    priority_mtb = {"imn": 4, "nmn": 3, "rmn": 2, "lmn": 1, "omn": 0,
                    "pmn": 0, "": 0}

    if network in priority_hike:
        return priority_hike[network]
    elif network in priority_cycle:
        return priority_cycle[network]
    elif network in priority_mtb:
        return priority_mtb[network]
    else:
        return 0


# return mtb network tag value corresponding to osm cycle network tag value
def network_cycle_to_mtb(network):
    network_dict = {"icn": "imn", "ncn": "nmn", "rcn": "rmn", "lcn": "lmn",
                    "ocn": "omn", "pcn": "pmn", "": ""}
    if network in network_dict:
        return network_dict[network]
    else:
        return ""


# return chw network tag value corresponding to osm cycle network tag value
def network_cycle_to_chw(network):
    network_dict = {"icn": "ich", "ncn": "nch", "rcn": "rch", "lcn": "lch",
                    "ocn": "och", "pcn": "pch", "": ""}
    if network in network_dict:
        return network_dict[network]
    else:
        return ""


# return osm tag value, replace "None" with ""
def get_tag(obj_tags, name):
    tag = obj_tags.get(name)
    if tag is None:
        return ""
    else:
        return tag


# delete key from dict
def del_key(dct, name):
    if name in dct.keys():
        del dct[name]


# delete keys from dict
def del_key_list(dct, name_list):
    for name in name_list:
        del_key(dct, name)


# Identify and return the relation of way_rel_list with the highest network
# priority. If this relation has an empty ref tag value, try to get one from
# another relation with the same priority (Backup 1). If there is none with
# a ref tag, use the ref tag of a relation with lower priority, if available
# (Backup 2).
def highest_priority_rel(way_rel_list):

    # Case 1: Only one parent relation.
    if len(way_rel_list) == 1:
        rel_result = way_rel_list[0]

    # Case 2: More than one parent relation.
    elif len(way_rel_list) > 1:
        priority = -1
        for i_rel, rel in enumerate(way_rel_list):
            if network_priority(rel["network"]) > priority:
                priority = network_priority(rel["network"])
                rel_result = rel

        # Backup 1
        if rel_result["ref"] == "":
            for rel in way_rel_list:
                if (network_priority(rel["network"]) == priority
                        and rel["ref"] != ""):
                    rel_result["ref"] = rel["ref"]
                    break

        # Backup 2
        if rel_result["ref"] == "":
            for rel in way_rel_list:
                if rel["ref"] != "":
                    rel_result["ref"] = rel["ref"]
                    break

    return rel_result


# Collect and prepare network, ref, mtb_role, osmc_dict for the highest
# priority route a way is member of. Determine via osmc_symbol dict whether
# way_id shoudl get an osmc symbol.
def get_route_data(way_rel_list, osmc_symbols, way_id):

    route_data = highest_priority_rel(way_rel_list)

    result = {}
    result["ref"] = route_data["ref"]
    result["network"] = route_data["network"]
    result["mtb_role"] = ""
    result["osmc"] = {}

    if "mtb_role" in route_data.keys():
        result["mtb_role"] = route_data["mtb_role"]

    # osmc symbol only not for all ways
    if "osmc" in route_data:
        result["osmc"] = route_data["osmc"]
        if osmc_symbols[route_data["id"]][way_id] == 1:
            result["osmc"]["symbol"] = "yes"
        else:
            result["osmc"]["symbol"] = "no"

    # mapsforge/tag-mapping: ref tag is not allowed to contain only numbers
    if result["ref"].isdigit():
        result["ref"] += " "

    return result


# Get route tag value if it matches the desired network_type.
def get_route_tag(r_tags, network_type):
    route_temp = get_tag(r_tags, "route").lower()

    if network_type in route_sets:
        route = ""
        for rt in route_temp.split(";"):
            if rt in route_sets[network_type]:
                route = rt
                break
        return route
    else:
        return ""


# Get network tag value if it matches the desired network_type.
# For mtb networks, transform cycle network to mtb network (e.g. lcn -> lmn)
def get_network_tag(r_tags, network_type):
    network_temp = get_tag(r_tags, "network").lower()

    if network_type in network_sets:
        network = ""
        for nw in network_temp.split(";"):
            if nw in network_sets[network_type]:
                network = nw
                break

        if network_type == "mtb":
            network = network_cycle_to_mtb(network)

        return network
    else:
        return ""


# check if route is in state proposed and change network accordingly
def check_proposed(r_tags, network, network_type):
    state_temp = get_tag(r_tags, "state").lower()
    if state_temp == "proposed":
        if network_type == "hk":
            return "pwn"
        if network_type == "cy":
            return "pcn"
        if network_type == "mtb":
            return "pmn"
    else:
        return network


# check if route is node network and change network accordingly
def check_node_network(r_tags, network, network_type):
    network_type_temp = get_tag(r_tags, "network:type").lower()
    if network_type_temp == "node_network":
        if network_type == "hk":
            return "own"
        if network_type == "cy":
            return "ocn"
        if network_type == "mtb":
            return "omn"
    else:
        return network


# add osmc waycolor to tag list and create a osmc symbol node if the ways
# should receive an osmc symbol (node is stored in osmc_nodes_hk)
def process_osmc_symbol_for_way(way, osmc, tag_list, osmc_nodes_hk):
    # "wc" in osmc.keys() --> check if osmc data exists
    if "wc" in osmc:
        if osmc["wc"] != "":
            tag_list["osmc_color"] = "wmco_" + osmc["wc"]

        if osmc["symbol"] == "yes":
            n_nodes = len(way.nodes)
            symbol_node = way.nodes[math.floor(n_nodes/2+0.5)].ref
            if symbol_node not in osmc_nodes_hk:
                osmc_nodes_hk[symbol_node] = []
            osmc_nodes_hk[symbol_node].append(osmc)


# extract osmc symbol data from osmc:symbol tag for hike route relations and
# store ist in osmc dict
def process_osmc_symbol_for_route(r_tags, osmc):
    osmc_valid = False
    osmc_temp = get_tag(r_tags, "osmc:symbol").split(":")

    # osmc:symbol=waycolor:background:foreground:text:textcolor
    # minimum requirement: waycolor, background and forground
    if len(osmc_temp) >= 3:
        osmc_valid = True
        osmc["wc"] = osmc_temp[0].lower()
        osmc["bg"] = osmc_temp[1].lower()
        osmc["fg"] = osmc_temp[2].lower()

        if not (osmc["wc"] in osmc_color or osmc["wc"] == ""):
            osmc_valid = False
        if not (osmc["bg"] in osmc_bg or osmc["bg"] == ""):
            osmc_valid = False
        if not (osmc["fg"] in osmc_fg or osmc["fg"] == ""):
            osmc_valid = False
        if not (osmc["wc"] != "" or osmc["bg"] != "" or osmc["fg"] != ""):
            osmc_valid = False

    # optional: text
    if len(osmc_temp) >= 4:
        # cut text to max 5 letters
        osmc["t"] = osmc_temp[3][:5]

    # optional: textcolor
    if len(osmc_temp) == 5:
        osmc["tc"] = osmc_temp[4].lower()
        if osmc_valid and osmc["tc"] in osmc_tc:
            osmc_valid = True
        else:
            osmc_valid = False

    return osmc_valid


# Add all member ways of a relation to osmc_symbols dict.
# (Later, funktion distribute_osmc_symbols will add the information wheter a
# way should receive an osmc symbol.)
def add_way_osmc(rel, osmc_symbols):
    osmc_symbols_temp = {}
    for m in rel.members:
        if m.type == "w":
            osmc_symbols_temp[m.ref] = ""
    osmc_symbols[rel.id] = osmc_symbols_temp


# Collect data necessarc for resolving route relations. Resolving route
# relations means to pass route tags from the route with the highest priority
# to the underlying ways. the following data is collected:
# - ways_hk/_cy/_mtb: dict to store all relations a way is member of
#                     {"way_id1": [{'id': '1', 'ref': '', 'route': '',
#                                   'network': ''}, {'id': '2', ...}, ...]
#                     {"way_id2": [...], ...}
# - ways_nodecount: dict of all ways with their number of nodes
#                   {"way_id1": x, "way_id2: y}
# - osmc_symbols: dict of all ways of every relation. Later, funktion
#                 distribute_osmc_symbols will add the information wheter a
#                 way should receive an osmc symbol. Value 1: Way should
#                 receive OSMC symbol. Value 0: No symbol.
#                 {"rel_id1": {'way_id1': 0, 'way_id2': 1, ...},
#                  "rel_id2": {'way_id3': 1, 'way_id3': 0, ..'},
#                  "rel_id3": {...}}
class collect_route_data(osmium.SimpleHandler):
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.ways_hk = {}
        self.ways_cy = {}
        self.ways_chw = {}
        self.ways_mtb = {}
        self.ways_nodecount = {}
        self.osmc_symbols = {}

    def relation(self, r):
        if r.tags.get("type") not in {"route", "network"}:
            return

        route_hk = get_route_tag(r.tags, "hk")
        route_cy = get_route_tag(r.tags, "cy")
        route_mtb = get_route_tag(r.tags, "mtb")

        network_hk = get_network_tag(r.tags, "hk")
        network_cy = get_network_tag(r.tags, "cy")
        network_mtb = get_network_tag(r.tags, "mtb")

        hk = False
        cy = False
        mtb = False

        # route tag or network is sufficient for hiking routes
        if route_hk != "" or network_hk != "":
            if network_hk == "":
                network_hk = "lwn"
            network_hk = check_proposed(r.tags, network_hk, "hk")
            network_hk = check_node_network(r.tags, network_hk, "hk")
            hk = True

        # route tag is necessary to differentiate between cylce/mtb
        if route_cy != "":
            if network_cy == "":
                network_cy = "lcn"
            network_cy = check_proposed(r.tags, network_cy, "cy")
            network_cy = check_node_network(r.tags, network_cy, "cy")
            cy = True

        # route tag is necessary to differentiate between cylce/mtb
        if route_mtb != "":
            if network_mtb == "":
                network_mtb = "lmn"
            network_mtb = check_proposed(r.tags, network_mtb, "mtb")
            network_mtb = check_node_network(r.tags, network_mtb, "mtb")
            mtb = True

        # only proceed if relation is a valid hike / cycle / mtb route
        if not (hk or cy or mtb):
            return

        ref = get_tag(r.tags, "ref")

        if hk:
            relation = {
                "id": r.id,
                "ref": ref,
                "route": route_hk,
                "network": network_hk,
            }

            # process osmc:symbol tag and store data if appropriate
            osmc = {}
            osmc_valid = process_osmc_symbol_for_route(r.tags, osmc)
            if osmc_valid:
                relation["osmc"] = osmc
                add_way_osmc(r, self.osmc_symbols)

            # add all member ways to route processing dict
            self.__add_ways(r.members, self.ways_hk, relation, False)

        if cy:
            relation = {
                "id": r.id,
                "ref": ref,
                "route": route_cy,
                "network": network_cy,
            }
            if get_tag(r.tags, "cycle_highway") == "yes":
                self.__add_ways(r.members, self.ways_chw, relation, False)
            else:
                self.__add_ways(r.members, self.ways_cy, relation, False)

        if mtb:
            relation = {
                "id": r.id,
                "ref": ref,
                "route": route_mtb,
                "network": network_mtb,
            }
            self.__add_ways(r.members, self.ways_mtb, relation, True)

    def way(self, w):
        self.ways_nodecount[w.id] = len(w.nodes)

    # add all members of type way to dictionary "ways", together with
    # information about the parent relation (rel_dict). For mtb-routes, add
    # role forwared/backward to rel_dict.
    def __add_ways(self, members, ways, rel_dict, mtb):
        for m in members:
            if m.type == "w":

                # for mtb-routes, preserve driving direction
                if mtb:
                    if m.role in {"forward", "backward"}:
                        rel_dict["mtb_role"] = m.role

                if m.ref not in ways:
                    ways[m.ref] = []
                ways[m.ref].append(rel_dict)


# All ways, which are part of of a hiking/cycle/mtb route inherit route
# relation tags (ref_hike/_cycle/_mtb, hknetwork/network/mtbnetwork) from the
# route with the highest priority.
# If split_mtb_cycle_ways is True, separate ways will be created for cycle and
# mtb routes.
# If a way should receive an osmc_symbol, identify the node and save it:
# - osmc_nodes_hk: dict of nodes which receive an osmc-symbol
#                  {"node_id1": osmc_dict1, "node_id2": osmc_dict2}
class process_route_ways(osmium.SimpleHandler):
    def __init__(self, ways_hk, ways_cy, ways_chw, ways_mtb, osmc_symbols,
                 writer):
        osmium.SimpleHandler.__init__(self)
        self.ways_hk = ways_hk
        self.ways_cy = ways_cy
        self.ways_chw = ways_chw
        self.ways_mtb = ways_mtb
        self.osmc_nodes_hk = {}
        self.osmc_symbols = osmc_symbols
        self.writer = writer
        self.way_id = -60000000000

    def way(self, w):
        hk = False
        cy = False
        mtb = False

        hk = w.id in self.ways_hk
        mtb = w.id in self.ways_mtb
        cy = w.id in self.ways_cy
        chw = w.id in self.ways_chw

        if not (hk or mtb or cy or chw):
            return

        tag_list = {}
        for k, v in w.tags:
            tag_list[k] = v

        if hk:
            res = get_route_data(self.ways_hk[w.id], self.osmc_symbols, w.id)

            tag_list["hknetwork"] = res["network"]
            tag_list["ref_hike"] = res["ref"]

            process_osmc_symbol_for_way(w, res["osmc"], tag_list,
                                        self.osmc_nodes_hk)

            if split_mtb_cycle_ways:
                # also for split_mtb_cycle_ways == True, hike-way overwrites
                # the original way
                way = w.replace(tags=tag_list)
                self.writer.add_way(way)

        if mtb:
            res = get_route_data(self.ways_mtb[w.id], self.osmc_symbols, w.id)

            tag_list["mtbnetwork"] = res["network"]
            tag_list["ref_mtb"] = res["ref"]
            if res["mtb_role"] != "":
                tag_list["mtb_role"] = res["mtb_role"]

            if split_mtb_cycle_ways:
                del_key_list(tag_list, ["ref_hike", "hknetwork", "osmc_color"])
                way = w.replace(id=self.way_id, tags=tag_list)
                self.writer.add_way(way)
                self.way_id = self.way_id + 1

        if cy:
            res = get_route_data(self.ways_cy[w.id], self.osmc_symbols, w.id)

            tag_list["network"] = res["network"]
            tag_list["ref_cycle"] = res["ref"]

            if split_mtb_cycle_ways:
                del_key_list(tag_list, ["ref_hike", "hknetwork", "osmc_color",
                                        "ref_mtb", "mtbnetwork"])
                way = w.replace(id=self.way_id, tags=tag_list)
                self.writer.add_way(way)
                self.way_id = self.way_id + 1

        if chw:
            res = get_route_data(self.ways_chw[w.id], self.osmc_symbols, w.id)

            tag_list["cycle_highway"] = network_cycle_to_chw(res["network"])
            tag_list["ref_chw"] = res["ref"]

            if split_mtb_cycle_ways:
                del_key_list(tag_list, ["ref_hike", "hknetwork", "osmc_color",
                                        "ref_mtb", "mtbnetwork",
                                        "ref_cycle", "network"])
                way = w.replace(id=self.way_id, tags=tag_list)
                self.writer.add_way(way)
                self.way_id = self.way_id + 1

        if not split_mtb_cycle_ways:
            way = w.replace(tags=tag_list)
            self.writer.add_way(way)


# add all available osmc tags to tag_list
def add_osmc_tags(tag_list, osmc):
    tag_list["osmc"] = "osmc_yes"
    if osmc["bg"] != "":
        tag_list["osmc_background"] = "wmbg_" + osmc["bg"]
    if osmc["fg"] != "":
        tag_list["osmc_foreground"] = "wmfg_" + osmc["fg"]
    if "t" in osmc.keys():
        tag_list["name"] = osmc["t"]
        tag_list["osmc_text_len"] = "wmtl_" + str(len(osmc["t"]))
    if "tc" in osmc.keys():
        tag_list["osmc_textcolor"] = "wmtc_" + osmc["tc"]


# All nodes, which should receive an osmc symbol according to dict
# osmc_nodes_hk get the appropriate tags added.
class process_osmc_nodes(osmium.SimpleHandler):
    def __init__(self, osmc_nodes_hk, writer):
        osmium.SimpleHandler.__init__(self)
        self.osmc_nodes_hk = osmc_nodes_hk
        self.writer = writer

    def node(self, n):
        if n.id in self.osmc_nodes_hk:

            # Node may have more than one symbol assinged (e.g. at an
            # intersection of ways.) In this unlikely case only the first
            # symbol is created, so issue a warning here.
            if len(self.osmc_nodes_hk[n.id]) > 1:
                print("    Warning, at least one duplicate osmc-symbol "
                      "ignored: %d" % n.id)

            # prepare tag list and add osmc tags
            tag_list = {}
            for k, v in n.tags:
                tag_list[k] = v
            osmc_tags = self.osmc_nodes_hk[n.id][0]
            add_osmc_tags(tag_list, osmc_tags)

            # delete foreground if background color is identical to foreground
            # color (redundant information)
            if osmc_tags["bg"] == osmc_tags["fg"].split("_")[0]:
                del_key(tag_list, "osmc_foreground")

            node = n.replace(tags=tag_list)
            self.writer.add_node(node)


# determine whether way should get osmc symbol
def distribute_osmc_symbols(osmc_symbols, ways_nodecount):
    for rel in osmc_symbols:
        # dictionary osmc_symbols[rel] is insertion ordered, so all ways of
        # a route are treated in the right order
        for way in osmc_symbols[rel]:
            if way in ways_nodecount:
                last_way_has_symbol = True

                # ways < 5 nodes: no osmc symbol
                if ways_nodecount[way] < 5:
                    osmc_symbols[rel][way] = 0

                # ways 5-10 nodes: every 2nd gets osmc symbol
                elif 5 <= ways_nodecount[way] <= 10:
                    if not last_way_has_symbol:
                        osmc_symbols[rel][way] = 1
                    last_way_has_symbol = not last_way_has_symbol

                # ways > 10 nodes: every way gets osmc symbol
                else:
                    osmc_symbols[rel][way] = 1

            # way is not included in osm data
            else:
                osmc_symbols[rel][way] = 0


def run(file_in, file_out):

    if os.path.exists(file_out):
        os.remove(file_out)

    writer = osmium.SimpleWriter(file_out)

    crd = collect_route_data()
    crd.apply_file(file_in)

    distribute_osmc_symbols(crd.osmc_symbols, crd.ways_nodecount)

    prw = process_route_ways(crd.ways_hk, crd.ways_cy, crd.ways_chw,
                             crd.ways_mtb, crd.osmc_symbols, writer)
    prw.apply_file(file_in)

    pon = process_osmc_nodes(prw.osmc_nodes_hk, writer)
    pon.apply_file(file_in)

    writer.close()
