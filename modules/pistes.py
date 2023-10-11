import osmium
import os
import time

import modules.reduce_data as reduce_data

tag_set = {"route", "piste:type", "piste:grooming", "piste:oneway",
           "piste:difficulty", "piste:ref", "piste:name"}


# Collect tag information of piste relations and store this information for
# all member ways
# - all_rels: dict of all piste relation member ways, value is a list of dicts
#             with piste tag information of all parent piste relations this way
#             is a member of.
class Collect_Piste_Rels(osmium.SimpleHandler):
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.way_rels = {}

    def relation(self, r):
        if r.tags.get("type") == "route" and r.tags.get("route") == "piste":

            tags = {}
            for k, v in r.tags:
                if k in tag_set:
                    tags[k] = v

            for m in r.members:
                if m.type == "w":
                    if m.ref not in self.way_rels:
                        self.way_rels[m.ref] = []
                    self.way_rels[m.ref].append(tags)


# Process two types of ways:
# Case 1: All ways that are part of a piste relation. These inherit piste
#         route tags from the relation (but way tag values have priority,
#         including difficulty) and get passed to the writer with a new way id.
# Case 2: Way itself has piste route/piste tags. Copy all piste relevant tags
#         and create a new way with these tags. The piste tags from the
#         original way will be cleared during tag-transform.
class Process_Piste_Ways(osmium.SimpleHandler):
    def __init__(self, way_rels, writer):
        osmium.SimpleHandler.__init__(self)
        self.way_rels = way_rels
        self.writer = writer
        self.way_id = -50000000000

    def way(self, w):
        # Case 1
        if w.id in self.way_rels:

            tags_way = {}
            for k, v in w.tags:
                if k in tag_set:
                    tags_way[k] = v

            # only use tags from first parent piste relation.
            # tag list of the way (inclding difficulty) has priority.
            tag_list = self.way_rels[w.id][0] | tags_way

            if "piste:oneway" in tag_list:
                tag_list["piste:oneway"] = "pow_" + tag_list["piste:oneway"]

            way = w.replace(id=self.way_id, tags=tag_list)
            self.writer.add_way(way)
            self.way_id = self.way_id + 1

        elif w.tags.get("route") == "piste" or "piste:type" in w.tags:

            tag_list = {}

            if "route" in w.tags:
                tag_list["route"] = w.tags.get("route")
            if "piste:type" in w.tags:
                tag_list["piste:type"] = w.tags.get("piste:type")
            if "piste:grooming" in w.tags:
                tag_list["piste:grooming"] = w.tags.get("piste:grooming")
            if "piste:oneway" in w.tags:
                tag_list["piste:oneway"] = "pow_" + w.tags.get("piste:oneway")
            if "piste:difficulty" in w.tags:
                tag_list["piste:difficulty"] = w.tags.get("piste:difficulty")
            if "piste:name" in w.tags:
                tag_list["piste:name"] = w.tags.get("piste:name")
            if "piste:ref" in w.tags:
                tag_list["piste:ref"] = w.tags.get("piste:ref")

            way = w.replace(id=self.way_id, tags=tag_list)
            self.writer.add_way(way)
            self.way_id = self.way_id + 1


def run(file_in, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    cpr = Collect_Piste_Rels()
    cpr.apply_file(file_in)

    temp_file = "tmp/temp_pistes.pbf"

    if os.path.exists(temp_file):
        os.remove(temp_file)
    writer = osmium.SimpleWriter(temp_file)

    ppw = Process_Piste_Ways(cpr.way_rels, writer)
    ppw.apply_file(file_in)

    writer.close()

    temp_file_sorted = "tmp/temp_pistes_sorted.pbf"
    cmd = "osmosis -q --rbf " + temp_file + " --s --wb " + temp_file_sorted
    os.system(cmd)

    # check tag limit
    temp_pistes_limit = "tmp/temp_pistes_tags_limited.pbf"
    reduce_data.run(temp_file_sorted, "", temp_pistes_limit)

    # merge original routes and routes with limited tags (last file has
    # highest priority for osmconvert"
    cmd = ("osmconvert " + temp_file_sorted + " "
           "| osmconvert - " + temp_pistes_limit + " "
           "--drop-version -o=" + file_out)
    os.system(cmd)

    os.remove(temp_file)
    os.remove(temp_file_sorted)
    os.remove(temp_pistes_limit)

    print("    %s seconds" % round((time.time() - start_time), 1))
