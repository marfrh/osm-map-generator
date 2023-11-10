import osmium
import os
import time

# redlist of tags to remove if a way exceeds the mapsforge 15 tags limit
redlist = ["mtb_scale_imba", "surface", "ref", "trail_visibility", "foot",
           "bicycle", "access", "mtb_scale_uphill", "mtb_scale", "sac_scale",
           "ref_hike", "ref_cycle", "incline_dir", "mtb_role", "ref_mtb"]

# relation types to delete entirely, but prevent ways from being deleted if
# the ways don't have relevant tags theirselves
rel_type_del_set1 = {"superroute", "route"}

# relation types to delete, don't prevent ways from being deleted if the ways
# don't have relevant tags theirselves
rel_type_del_set2 = {"route_master", "collection", "network", "classification",
                     "tmc", "site", "watershed", "defaults", "multilinestring",
                     "linestring", "tmc:area"}

# boundary relations to delete. all necessary boundaries like mountain_areas
# should already exist as separate polygon labels
rel_boundary_del_set = {"political", "educational", "historic_church_province",
                        "statistical_region", "statistical", "ceremonial",
                        "vice_county", "local_authority", "traditional",
                        "administrative_cooperation", "historic", "police",
                        "civil_defense", "land_area", "region", "natural",
                        "timezone", "administrative"}

# place multipolygons to delete (not necessary as coastlines are handled by
# land polygons)
mp_place_del_set = {"island", "islet", "archipelago", "sea", "ocean",
                    "peninsula", "bay"}

# natural multipolygons to delete
mp_natural_del_set = {"peninsula", "strait", "bay"}

# Blacklist / whitlist for relations to always delete or always keep.
# E.g. large coastline relations slowing down mapsforge-writer.
blacklist = {9516330}
whitelist = {3474227}

# mapsforge tag limit per way
threshold = 15


# read an xml file and add all osm tag keys identified by preceeding
# key_identifier and key_end to target_set. Multiple keys can be separated
# by "|".
def read_xml_keys(file_in, target_set, key_identifier, key_end):
    f = open(file_in, "r")
    content = f.readlines()
    f.close()

    for line in content:
        key_found = line.find(key_identifier)
        if key_found > 0:
            start = key_found+len(key_identifier)+1
            end = start+line[start:].find(key_end)
            key = line[start:end]
            if key != "*":
                if key.find("|") > 0:
                    keys = key.split("|")
                    for k in keys:
                        target_set.add(k)
                else:
                    target_set.add(key)


# read up to two tagmapping-files and up to two xml map themes and return their
# osm tag keys as key_set
def read_osm_tag_keys(tm1, tm2, theme1, theme2):
    key_set = set()
    if tm1 != "":
        read_xml_keys(tm1, key_set, "key=", "'")
    if tm2 != "":
        read_xml_keys(tm2, key_set, "key=", "'")
    if theme1 != "":
        read_xml_keys(theme1, key_set, "k=", "\"")
    if theme2 != "":
        read_xml_keys(theme2, key_set, "k=", "\"")

    return key_set


# This class mainly does three things:
# 1. Check relations if they can be deleted or have relevant tags, see comments
#    below.
# 2. Check ways if they are candidates for deletion based on their tags.
# 3. Check the maspforge writer tag limt per way and reduce way tags (according
#    to redlist) if necessary.
class collect_data_and_limit_tags(osmium.SimpleHandler):
    def __init__(self, threshold, writer_limit, key_set):
        osmium.SimpleHandler.__init__(self)
        self.threshold = threshold
        self.writer_limit = writer_limit
        self.key_set = key_set

        # set of all osm ways (ids) that are members of a relation with
        # one or more tags of key_set
        self.relation_ways = set()

        # Relation to be deleted. Member ways of these relations will not be
        # added to self.relation_ways as they don't need to be kept.
        self.del_rels = set()

        # Relations to be deleted. Member ways of these relations should not be
        # deleted and are added to self.relation_ways.
        self.del_rels_with_relevant_ways = set()

        # Ways that are candidates to be deleted because of their tags.
        self.del_ways = set()
        self.coastline_ways = set()

    def relation(self, r):
        if r.id in blacklist:
            self.del_rels.add(r.id)
            return

        if r.id in whitelist:
            self.__add_members_to_relation_ways(r.members)
            return

        relevant = self.__check_tags(r.id, r.tags)

        if relevant is False:
            self.del_rels.add(r.id)
        else:
            self.__add_members_to_relation_ways(r.members)

    def way(self, w):
        # Store ways without relevant tags (defined by key_set) and store
        # coastline ways
        relevant = False
        tags = {}
        for k, v in w.tags:
            tags[k] = v
            if k in self.key_set:
                relevant = True
        if relevant is False:
            self.del_ways.add(w.id)

        if "natural" in tags:
            if tags["natural"] == "coastline":
                self.coastline_ways.add(w.id)

        # Check mapsforge-writer tag limit and reduce tags if necessary.
        self.__check_tag_limit(w, tags)

    def __add_members_to_relation_ways(self, members):
        for m in members:
            if m.type == "w":
                self.relation_ways.add(m.ref)

    def __check_tags(self, r_id, r_tags):
        relevant = False
        for k, v in r_tags:

            # Relation should be deleted, but member ways should not. For
            # example, member ways of a route relation should not be deleted
            # (they inherit route tags in other subroutines).
            if k == "type" and v.lower() in rel_type_del_set1:
                self.del_rels_with_relevant_ways.add(r_id)

            # Always delete these relations and don't exclude the member ways
            # from possible deletion (only if they have relevant tags
            # theirselves).
            elif k == "type" and v.lower() in rel_type_del_set2:
                relevant = False
                break

            elif k == "boundary" and v.lower() in rel_boundary_del_set:
                relevant = False
                break

            elif k == "boundary" and r_tags.get("historic") == "yes":
                relevant = False
                break

            elif k == "boundary" and r_tags.get("border_type") == "baseline":
                relevant = False
                break

            elif k == "type" and v.lower() == "multipolygon":
                if r_tags.get("place") in mp_place_del_set:
                    relevant = False
                    break
                if r_tags.get("natural") in mp_natural_del_set:
                    relevant = False
                    break

            # Keep relation if it has relevant tags. Member ways will also be
            # excluded from deletion.
            elif k in self.key_set:
                relevant = True

        return relevant

    def __check_tag_limit(self, w, tags):
        if len(tags.keys()) > self.threshold:
            n = 0
            for t in tags.keys():
                # only count relevant tags
                if t in self.key_set:
                    n = n + 1

            # reduce tags if necessary
            if n > self.threshold:
                for r in redlist:
                    tags.pop(r, None)
                    if len(tags.keys()) <= self.threshold:
                        break

                way = w.replace(tags=tags)
                self.writer_limit.add_way(way)


# pass an empty way with id w_id to the writer
def write_empty_way(writer, w_id):
    w = osmium.osm.Way("").replace(id=w_id, nodes=[], version=1, visible=True,
                                   changeset=1,
                                   timestamp="1970-01-01T00:59:59Z", uid=1,
                                   user="", tags=[])
    writer.add_way(w)


# pass an empty relation with osm id r_id to the writer
def write_empty_relation(writer, r_id):
    r = osmium.osm.Relation("").replace(id=r_id, members=[], version=1,
                                        visible=True, changeset=1,
                                        timestamp="1970-01-01T00:59:59Z",
                                        uid=1, user="", tags=[])
    writer.add_relation(r)


def run(file_in, file_out_subtract, file_out_limit):
    if os.path.exists(file_out_subtract) and os.path.exists(file_out_limit):
        print("    Files %s and %s already exists."
              % (file_out_subtract, file_out_limit))
        return

    start_time = time.time()

    tm1 = "tt_tm/tagmapping-urban.xml"
    tm2 = "tt_tm/tagmapping-min.xml"
    theme1 = "themes/Elevate/Elevate.xml"
    theme2 = "themes/Elevate/Elements.xml"

    # read relevant osm keys from tag-mapping and map themes
    key_set = read_osm_tag_keys(tm1, tm2, theme1, theme2)
    key_set.remove("bBoxWeight")

    if os.path.exists(file_out_limit):
        os.remove(file_out_limit)
    writer_limit = osmium.SimpleWriter(file_out_limit)

    # collect data
    cd = collect_data_and_limit_tags(threshold, writer_limit, key_set)
    cd.apply_file(file_in)
    writer_limit.close()

    # Exit here if file_out_subtract is not needed. Don't print elapsed
    # time because in this case only the tag limit part is used as part of
    # other subroutines.
    if file_out_subtract == "":
        return

    # is the way in a relation that has relevant tags?
    del_ways2 = set()
    for w in cd.del_ways:
        if w not in cd.relation_ways:
            del_ways2.add(w)

    # also delete coastlines that are in no relation
    for w in cd.coastline_ways:
        if w not in cd.relation_ways:
            del_ways2.add(w)
            break

    # prepare output file
    temp_file_subtract = "tmp/temp_subtract.pbf"
    if os.path.exists(temp_file_subtract):
        os.remove(temp_file_subtract)
    writer = osmium.SimpleWriter(temp_file_subtract)

    for w in del_ways2:
        write_empty_way(writer, w)
    print("    %d ways deleted" % len(del_ways2))

    del_rels = cd.del_rels
    del_rels.update(cd.del_rels_with_relevant_ways)

    for r_id in del_rels:
        write_empty_relation(writer, r_id)
    print("    %d relations deleted" % len(del_rels))

    writer.close()

    # temp file is not sorted yet --> sort
    cmd = "osmosis -q --rbf " + temp_file_subtract + " --s --wb "
    cmd += file_out_subtract
    os.system(cmd)
    os.remove(temp_file_subtract)

    print("    %s seconds" % round((time.time() - start_time), 1))
