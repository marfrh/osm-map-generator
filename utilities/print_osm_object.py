#!/usr/bin/python3

import argparse
import osmium


def print_tag_list(tags):
    print("Tag list: ", end="")
    temp_str = ""
    for k, v in tags:
        temp_str += str(k) + "=" + str(v) + ", "
    print(temp_str[:-2])


class print_relation(osmium.SimpleHandler):
    def __init__(self, rel_id):
        osmium.SimpleHandler.__init__(self)
        self.rel_id = rel_id
        self.found = False

    def relation(self, r):
        if self.found:
            return

        if r.id == self.rel_id:
            print("\nRelation id: %d" % r.id)

            refs = []
            refs.extend([m.ref, m.role] for m in r.members)
            print("Members: ", end="")
            temp_str = ""
            for ref in refs:
                temp_str += str(ref[0]) + ": " + str(ref[1]) + ", "
            print(temp_str[:-2])

            print_tag_list(r.tags)

            self.found = True


class print_way(osmium.SimpleHandler):
    def __init__(self, way_id):
        osmium.SimpleHandler.__init__(self)
        self.way_id = way_id
        self.found = False

    def way(self, w):
        if self.found:
            return

        if w.id == self.way_id:
            print("Way id: %d" % w.id)

            refs = []
            refs.extend(n for n in w.nodes)
            print("Nodes: ", end="")
            temp_str = ""
            for n in refs:
                temp_str += str(n) + ", "
            print(temp_str[:-2])

            print_tag_list(w.tags)

            self.found = True


class print_node(osmium.SimpleHandler):
    def __init__(self, node_id):
        osmium.SimpleHandler.__init__(self)
        self.node_id = node_id
        self.found = False

    def node(self, n):
        if self.found:
            return

        if n.id == self.node_id:
            print("Node id: %d" % n.id)

            print_tag_list(n.tags)

            self.found = True


def run(file_in, node_id, way_id, rel_id):
    print("Start reading osm data.")

    if rel_id is not None:
        print("\nSearching relation, this may take a while.")
        pr = print_relation(rel_id)
        pr.apply_file(file_in)

    if way_id is not None:
        print("\nSearching way, this may take a while.")
        pw = print_way(way_id)
        pw.apply_file(file_in)

    if node_id is not None:
        print("\nSearching node, this may take a while.")
        pn = print_node(node_id)
        pn.apply_file(file_in)

    print("\nFinished.")


if __name__ == "__main__":

    name = "Print osm object"
    descr = ("Script to print a single osm object.")
    epilog = "https://github.com/marfrh/osm-map-generator"

    p = argparse.ArgumentParser(prog=name,
                                description=descr,
                                epilog=epilog)
    p.add_argument("file_in",
                   help="Input file (osm, pbf)")
    p.add_argument("-n",
                   "--node_id",
                   type=int,
                   help="Node id to print.")
    p.add_argument("-w",
                   "--way_id",
                   type=int,
                   help="Way id to print.")
    p.add_argument("-r",
                   "--rel_id",
                   type=int,
                   help="Relation id to print.")
    args = p.parse_args()

    if args.node_id or args.way_id or args.rel_id:
        run(args.file_in, args.node_id, args.way_id, args.rel_id)
    else:
        print("No id specified.")
