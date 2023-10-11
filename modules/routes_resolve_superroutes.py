import os
import osmium


# blacklist of relations that should not inherit to other relations
# e.g. relations like "Wanderwege in den Ostalpen",
# "Jakobswege in Deutschland", "Wanderwege in den Gailtaler Alpen"
blacklist = {223156, 3235848, 9197048}


# return True if network1 has higher priority than network2
def pass_network(network1, network2):
    nw_list = [network1, network2]
    nw_type = ["", ""]
    nw_prio = ["", ""]
    cycle_dict = {"icn": 4, "ncn": 3, "rcn": 2, "lcn": 1, "": 0}
    hike_dict = {"iwn": 4, "nwn": 3, "rwn": 2, "lwn": 1, "": 0}

    # determin nw_type and nw_prio for all elements in nw_list
    for nw_index, nw in enumerate(nw_list):
        if nw in cycle_dict:
            nw_type[nw_index] = "cycle"
            nw_prio[nw_index] = cycle_dict[nw_list[nw_index]]
        if nw in hike_dict:
            nw_type[nw_index] = "hike"
            nw_prio[nw_index] = hike_dict[nw_list[nw_index]]

    # case 1, same network type: only pass tags if priority of network1 is
    # higher, e.g. ncn overwrites rcn.
    if nw_type[0] == nw_type[1]:
        if nw_prio[0] > nw_prio[1]:
            return True
        else:
            return False
    # case 2: different network type: always pass network tag, e.g. if a
    # mtb-superroute (rcn) contains a hiking route (rwn): rcn overwrites rwn.
    else:
        # Rad-Relation soll auf Wander-Relation vererben und umgekehrt
        return True


# return True if r is of network:type node_network
def is_node_network(r_tags):
    type_tag = r_tags.get("type")
    nw_type_tag = r_tags.get("network:type")

    if nw_type_tag == "node_network" and type_tag == "network":
        return True
    else:
        return False


# return a list of network types (lwn, lcn, ...)
def get_network(r_tags):
    network_tag = r_tags.get("network")
    if network_tag is None:
        network = [""]
    else:
        network = network_tag.lower().replace(" ", "").split(";")
        for nw in network:
            if nw not in {"iwn", "nwn", "rwn", "lwn", "icn", "ncn", "rcn",
                          "lcn"}:
                nw = ""
    return network


def get_cycle_highway(r_tags):
    if r_tags.get("cycle_highway") == "yes":
        return "yes"
    else:
        return ""


# return True if one of the route tag values represents a hike/cycle/mtb route
def route_tag_is_valid(r_tags):
    route_tag = r_tags.get("route")
    valid = False
    if route_tag is not None:
        route_tag = route_tag.lower().replace(" ", "").split(";")
        for rt in route_tag:
            if rt in {"bicycle", "mtb", "foot", "walking", "hiking"}:
                valid = True
                break
    return valid


# Collect data for routes and superroutes (superroutes are route or
# node_network relations that contain other relations
#
# all_routes: dict wiht information for each route, keys are osm ids:
# - network: list of network values, e.g. ["lwn" "lcn"]
# - member_rels: list of member relation osm ids
#
# superroute_member_list: List of dicts containing relations that are members
#                         of a superroute relation plus additional information.
#                         If the parent superroute relation has multiple
#                         network values (e.g. lwn, lcn), a separate
#                         superroute-member is added for every network type.
# - srm_id: osm id of the superroute member relation
# - parent_id: osm id of the parent superroute
# - parent_name: name tag value of the parent superroute
# - parent_ref: ref tag value of the parent superroute
# - parent_network: network tag value for this superroute member relation
class collect_route_data(osmium.SimpleHandler):
    def __init__(self, superroute_member_list):
        osmium.SimpleHandler.__init__(self)
        self.superroute_member_list = superroute_member_list
        self.all_routes = {}

    def relation(self, r):
        if r.tags.get("type") not in {"route", "superroute", "network"}:
            return

        if not route_tag_is_valid(r.tags) and not is_node_network(r.tags):
            return

        # add relation to all_routes, together with list of network tyes add
        # relation member list
        member_rel_list = []
        member_rel_list.extend(m.ref for m in r.members if m.type == "r")
        network = get_network(r.tags)
        route_temp = {
            "network": network,
            "member_rels": member_rel_list,
            "cycle_highway": get_cycle_highway(r.tags)
        }
        self.all_routes[r.id] = route_temp

        # add all member relations to self.superroute_member_list
        self.__add_members_to_superroute_list(r, network)

    # add all member relations of r to superroute_member_list (passed by ref),
    # one entry per network type (e.g. lwn, lcn, ...)
    def __add_members_to_superroute_list(self, r, network):
        ref_temp = r.tags.get("ref")
        if ref_temp is None:
            ref_temp = ""

        for m in r.members:
            if m.type == "r":
                for nw in network:
                    superroute_member = {
                        "srm_id": m.ref,
                        "parent_id": r.id,
                        "parent_name": r.tags.get("name"),
                        "parent_ref": ref_temp,
                        "parent_network": nw
                    }
                    self.superroute_member_list.append(superroute_member)


# For all relations in target_dict, create a copy and inherit name/ref/network
# tags from the relation inidcated by src_index.
# All other relations, ways and nodes are passed to the writer unchanged.
class rel_copy(osmium.SimpleHandler):
    def __init__(self, target_dict, superroute_member_list, writer):
        osmium.SimpleHandler.__init__(self)
        self.target_dict = target_dict
        self.superroute_member_list = superroute_member_list
        self.writer = writer
        self.rel_id = -70000000000

    def relation(self, r):

        # copy every relation to output (unchanged)
        self.writer.add_relation(r)

        # if a superroute member relation should inherit tags from its parent
        # superroute, creat a duplicate of this relation and replace
        # name/ref/network tags with the values from the parent superroute
        if r.id in self.target_dict:

            # relation can be part of multiple superoutes
            for src_index in self.target_dict[r.id]:
                src_tags = self.superroute_member_list[src_index]

                tag_list = {}
                for k, v in r.tags:
                    tag_list[k] = v
                name = src_tags["parent_name"]
                if name is not None:
                    tag_list["name"] = name
                ref = src_tags["parent_ref"]
                if ref is not None:
                    tag_list["ref"] = ref
                network = src_tags["parent_network"]
                if network is not None:
                    tag_list["network"] = network

                rel = r.replace(id=self.rel_id, tags=tag_list)
                self.writer.add_relation(rel)
                self.rel_id += 1

    def way(self, w):
        self.writer.add_way(w)

    def node(self, n):
        self.writer.add_node(n)


def run(file_in, file_out):
    # dict to store which relation to duplicate (srm_id) and which parent
    # tags to use (srm_index)
    # {'srm_id1': [srm_index1, srm_index2], 'srm_id2': [...], ...}
    target_dict = {}

    superroute_member_list = []
    crd = collect_route_data(superroute_member_list)
    crd.apply_file(file_in)

    # Resolve al superroutes by passing network/name/ref from parent superroute
    # relation to member relations if the parent superroute has a higher
    # network priority.
    # If a superroute member (srm) inherits higher priority network/name/ref
    # tags from its parent superroute relations, it should pass these
    # network/ref/name tags to its relation members (if it has some). Therefore
    # append its member relations at the end of superroute_member_list.
    for srm_index, srm in enumerate(superroute_member_list):

        # Skip if srm_id is not part of the osm dataset
        srm_id = srm["srm_id"]
        if srm_id not in crd.all_routes:
            continue

        # Skip superroute member if parent superroute does not have a network
        # tag
        parent_network = srm["parent_network"]
        if parent_network == "":
            continue

        # superroute member can have multiple network tags
        for nw in crd.all_routes[srm_id]["network"]:

            # only pass network/name/ref of higher priority
            if parent_network != nw and pass_network(parent_network, nw):

                # Do not inherit from parent superroute if parent ist included
                # in blacklist
                if srm["parent_id"] in blacklist:
                    break

                # Do not inherit from parent superroute if cycle_highway tag
                # is different
                member_chw = crd.all_routes[srm_id]["cycle_highway"]
                parent_chw = crd.all_routes[srm["parent_id"]]["cycle_highway"]
                if member_chw != parent_chw:
                    break

                # To pass network/name/ref from parent superroute to member
                # relation in osm data, a new copy of the member relation with
                # these tags has to be created. Here, remember which relation
                # to duplicate (srm_id) and which parent tags to use
                # (srm_index).
                if srm_id not in target_dict:
                    target_dict[srm_id] = []
                target_dict[srm_id].append(srm_index)

                # loop through member relations of srm and add
                # these to superroute_member_list
                for m in crd.all_routes[srm_id]["member_rels"]:
                    superroute_member = {
                        "srm_id": m,
                        "parent_id": srm["parent_id"],
                        "parent_network": srm["parent_network"],
                        "parent_name": srm["parent_name"],
                        "parent_ref": srm["parent_ref"],
                    }
                    superroute_member_list.append(superroute_member)

    if os.path.exists(file_out):
        os.remove(file_out)
    writer = osmium.SimpleWriter(file_out)

    # perform copy operations
    rel_maker = rel_copy(target_dict, superroute_member_list, writer)
    rel_maker.apply_file(file_in)
    writer.close()
