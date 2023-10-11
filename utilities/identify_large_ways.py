#!/usr/bin/python3

import argparse
import osmium


class collect_way_data(osmium.SimpleHandler):
    def __init__(self, threshold):
        osmium.SimpleHandler.__init__(self)
        self.way_data = {}
        self.threshold = threshold

    def way(self, w):
        node_count = len(w.nodes)

        if node_count > self.threshold:
            tag_list = {}
            for k, v in w.tags:
                tag_list[k] = v

            data = {
                "tags": tag_list,
                "node_count": node_count,
                }
            self.way_data[w.id] = data


def run(file_in, threshold_nodes):
    print("Start reading osm data.")

    cwd = collect_way_data(threshold_nodes)
    cwd.apply_file(file_in)

    print("\n*** Results: ")
    for w in cwd.way_data:

        # non osm-objects
        if w < 0 or w > 100000000000 or "ele" in cwd.way_data[w]["tags"]:
            print("id: %d, no link, irregular osm object" % w)
            print("way node count: %d" % cwd.way_data[w]["node_count"])
            print("tags: %s\n" % cwd.way_data[w]["tags"])

        # regular osm objects
        else:
            print("id: %d, link: http://www.openstreetmap.org/way/%s" %
                  (w, str(w)))
            print("way node count: %d" % cwd.way_data[w]["node_count"])
            print("tags: %s\n" % cwd.way_data[w]["tags"])

    if not cwd.way_data:
        print("No ways with more than %d nodes found.\n" % threshold_nodes)

    print("Finished.")


if __name__ == "__main__":

    name = "Identify Large Ways"
    descr = ("Script to identify large osm ways by node count.")
    epilog = "https://github.com/marfrh/osm-map-generator"

    p = argparse.ArgumentParser(prog=name, description=descr, epilog=epilog)
    p.add_argument("file_in",
                   help="Input file to analyze (osm, pbf)")
    p.add_argument("-n",
                   "--node_threshold",
                   type=int,
                   default=2000,
                   help="Ways with nodes > node_threshold will be analyzed.")
    args = p.parse_args()

    run(args.file_in, args.node_threshold)
