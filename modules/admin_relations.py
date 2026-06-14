import os
import osmium
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')


# Collect data for all admin relations with admin_level 1-4. other admin_level
# relations will be deleted.
class collect_admin_relation_ways(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.all_ways = {}

    def relation(self, r):
        admin_level = r.tags.get("admin_level")

        if admin_level is None:
            return

        if not admin_level.isnumeric():
            return

        # only resolve administrative boundaries
        # e.g. no "historic" boundaries. Add other relations to ids_to_delete.
        if r.tags.get("boundary") != "administrative":
            return

        # only add admin levels 1-4 to all_ways, other admin levels should not
        # be resolved
        if int(admin_level) in [1, 2, 3, 4]:
            self.__add_members(r, int(admin_level))

    # Add all member ways of relation r to dict all_ways with r's admin level
    def __add_members(self, r, admin_level):
        for m in r.members:
            if m.type == "w":
                if m.ref not in self.all_ways:
                    self.all_ways[m.ref] = []
                self.all_ways[m.ref].append(admin_level)


# Pass ways in all_ways to the writer, but only for the lowest admin_level
# (= highest priority) if they are part of multiple admin-relations.
class process_ways(osmium.SimpleHandler):
    def __init__(self, all_ways, way_writer):
        super().__init__()
        self.all_ways = all_ways
        self.way_writer = way_writer
        self.way_id = -40000000000

    def way(self, w):
        if w.id in self.all_ways:

            # Don't pass admin_level tag to coastline ways
            if w.tags.get("natural") == "coastline":
                return

            # If the way is part of multiple admin_relations, only use the
            # lowest admin_level (= highest priority).
            rel_tags = {}
            rel_tags["admin_level"] = str(min(self.all_ways[w.id]))

            way = w.replace(id=self.way_id, tags=rel_tags)
            self.way_writer.add_way(way)
            self.way_id += 1


def run(file_in, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        logging.info(f"    File {file_out} already exists.")
        return

    temp_file = "tmp/temp_admin_ways.pbf"

    carw = collect_admin_relation_ways()
    try:
        carw.apply_file(file_in)
    except Exception as e:
        logging.error(f"Error reading file {file_in}: {e}")
        return

    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except OSError as e:
            logging.error(f"Failed to remove file {temp_file}: {e}")

    try:
        with osmium.SimpleWriter(temp_file) as way_writer:
            pw = process_ways(carw.all_ways, way_writer)
            pw.apply_file(file_in)
    except Exception as e:
        logging.error(f"Error processing ways: {e}")
        return

    # sort output file
    cmd = f"osmosis -q --rbf {temp_file} --s --wb {file_out} omitmetadata=true"
    result = os.system(cmd)
    if result != 0:
        logging.error(f"osmosis failed with exit code {result}")
        return

    try:
        os.remove(temp_file)
    except OSError as e:
        logging.error(f"Failed to remove file {temp_file}: {e}")

    logging.info(f"    {round((time.time() - start_time), 1)} seconds")
