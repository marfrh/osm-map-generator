import csv
import osmium
import os
import time


# Attach pead dominance tag from peak_data to all peaks/vocanos and attach
# saddle direction from saddle_data to all saddles. The original nodes are
# overwritten.
class process_peaks_saddles(osmium.SimpleHandler):
    def __init__(self, writer, peak_data, saddle_data):
        osmium.SimpleHandler.__init__(self)
        self.writer = writer
        self.peak_data = peak_data
        self.s_peak = set(peak_data[0])
        self.saddle_data = saddle_data
        self.s_saddle = set(saddle_data[0])

    def node(self, n):
        natural = n.tags.get("natural")
        mountain_pass = n.tags.get("mountain_pass")

        # Peaks
        if natural in ["peak", "volcano"]:

            if str(n.id) in self.s_peak:
                i = self.peak_data[0].index(str(n.id))
                pd = self.__dominance_to_dist_group(self.peak_data[3][i])
            else:
                pd = "pd_5"

            tag_list = {}
            for k, v in n.tags:
                tag_list[k] = v
            tag_list["peak_dist"] = pd

            node = n.replace(tags=tag_list)
            self.writer.add_node(node)

        # Saddles
        elif natural in ["saddle", "notch", "col"] or mountain_pass == "yes":
            if str(n.id) in self.s_saddle:
                i = self.saddle_data[0].index(str(n.id))
                sd = "ds_" + self.saddle_data[3][i]

                tag_list = {}
                for k, v in n.tags:
                    tag_list[k] = v
                tag_list["dir_saddle"] = sd

                node = n.replace(tags=tag_list)
                self.writer.add_node(node)

    # map peak dominance to pd_x tags
    def __dominance_to_dist_group(self, dominance):
        dom = int(dominance)
        if dom < 1200:
            dist_group = "pd_5"
        elif dom < 5000:
            dist_group = "pd_4"
        elif dom < 9000:
            dist_group = "pd_3"
        elif dom < 25000:
            dist_group = "pd_2"
        elif dom < 100000000:
            dist_group = "pd_1"

        return dist_group


def run(file_in, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    tmp_file = file_out[:-3] + "o5m"
    cmd = ("osmfilter " + file_in + " "
           "--parameter-file=osmfilter_parameters/peaks_saddles.txt "
           "-o=" + tmp_file)
    os.system(cmd)

    ti = "popcat_peaks_saddles/topographic_isolation_viefinderpanoramas.txt"
    sd = "popcat_peaks_saddles/saddledirection_viefinderpanoramas.100.txt"

    # read peaks and saddles input file and transpose and convert both to lists
    f = open(ti, mode="r", newline="\n")
    reader = csv.reader(filter(lambda row: row[0] != '#', f), delimiter=';')
    # ID;LON;LAT;dominance
    peak_data = list(zip(*reader))
    f.close()

    f = open(sd, mode="r", newline="\n")
    reader = csv.reader(filter(lambda row: row[0] != '#', f), delimiter=';')
    # ID;LON;LAT;direction
    saddle_data = list(zip(*reader))
    f.close()

    if os.path.exists(file_out):
        os.remove(file_out)
    writer = osmium.SimpleWriter(file_out)

    peak_saddle_parser = process_peaks_saddles(writer, peak_data, saddle_data)
    peak_saddle_parser.apply_file(tmp_file)

    writer.close()

    os.remove(tmp_file)

    print("    %s seconds" % round((time.time() - start_time), 1))
