#!/usr/bin/python3

import argparse
import osmium


class collect_relation_member_data(osmium.SimpleHandler):
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.relation_data = {}
        self.member_ways = {}

    def relation(self, r):
        tag_list = {}
        for k, v in r.tags:
            tag_list[k] = v

        rel_data = {
            "tags": tag_list,
            "is_nested": False,
            "member_relations": set(),
            "way_member_count": 0,
            "way_members": set()
            }

        for m in r.members:
            if m.type == "r":
                rel_data["member_relations"].add(m.ref)
                rel_data["is_nested"] = True

            if m.type == "w":
                rel_data["way_member_count"] += 1
                rel_data["way_members"].add(m.ref)

                if m.ref not in self.member_ways:
                    self.member_ways[m.ref] = []
                self.member_ways[m.ref].append(r.id)

        self.relation_data[r.id] = rel_data


# Store node count for all ways that are members in a relation
class collect_way_node_count(osmium.SimpleHandler):
    def __init__(self, member_ways):
        osmium.SimpleHandler.__init__(self)
        self.member_ways = member_ways
        self.way_node_count = {}

    def way(self, w):
        if w.id in self.member_ways:
            self.way_node_count[w.id] = len(w.nodes)


def run(file_in, threshold_nodes, threshold_ways):
    print("Start reading osm data.")

    crmd = collect_relation_member_data()
    crmd.apply_file(file_in)

    cwnc = collect_way_node_count(crmd.member_ways)
    cwnc.apply_file(file_in)

    # Sum up node count for each relation:
    for rel in crmd.relation_data:
        rel_data = crmd.relation_data[rel]
        rel_data["node_count"] = 0
        for way_id in rel_data["way_members"]:
            if way_id in cwnc.way_node_count:
                rel_data["node_count"] += cwnc.way_node_count[way_id]

    # Calculate total node count and way member count for nested relations and
    # store relation id if node count / way mamber count are above threshold.
    results_ways = set()
    results_nodes = set()
    for rel in crmd.relation_data:
        rel_data = crmd.relation_data[rel]

        rel_data["way_member_count_total"] = rel_data["way_member_count"]
        rel_data["node_count_total"] = rel_data["node_count"]

        if rel_data["is_nested"] is True:
            for m in rel_data["member_relations"]:

                # member relation might no be included in data
                if m in crmd.relation_data:
                    way_count_temp = crmd.relation_data[m]["way_member_count"]
                    rel_data["way_member_count_total"] += way_count_temp

                    node_count_temp = crmd.relation_data[m]["node_count"]
                    rel_data["node_count_total"] += node_count_temp

        if rel_data["way_member_count_total"] > threshold_ways:
            results_ways.add(rel)

        if rel_data["node_count_total"] > threshold_nodes:
            results_nodes.add(rel)

    print("\n*** Way results: ")
    for r in results_ways:
        print("id: %d, link: http://www.openstreetmap.org/relation/%s" %
              (r, str(r)))
        print("way member count total: %d" %
              crmd.relation_data[r]["way_member_count_total"])
        print("tags: %s\n" % crmd.relation_data[r]["tags"])

    if not results_ways:
        print("No relations with more than %d ways found.\n" % threshold_ways)

    print("*** Node results: ")
    for r in results_nodes:
        print("id: %d, link: http://www.openstreetmap.org/relation/%s" %
              (r, str(r)))
        print("node count total: %d" %
              crmd.relation_data[r]["node_count_total"])
        print("tags: %s\n" % crmd.relation_data[r]["tags"])

    if not results_nodes:
        print("No relations with more than %d nodes found.\n" %
              threshold_nodes)

    print("Finished.")


if __name__ == "__main__":

    name = "Identify Large Relations"
    descr = ("Script to identify large osm relations (including nested "
             "relations) by node count and way member count. ")
    epilog = "https://github.com/marfrh/osm-map-generator"

    p = argparse.ArgumentParser(prog=name, description=descr, epilog=epilog)
    p.add_argument("file_in",
                   help="Input file to analyze (osm, pbf)")
    p.add_argument("-n",
                   "--node_threshold",
                   type=int,
                   default=50000,
                   help="Relations with nodes > node_threshold will be "
                   "analyzed.")
    p.add_argument("-w",
                   "--way_member_threshold",
                   type=int,
                   default=2000,
                   help="Relations with way_members > way_member_threshold "
                   "will be analyzed.")
    args = p.parse_args()

    run(args.file_in, args.node_threshold, args.way_member_threshold)
