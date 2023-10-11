import csv
import osmium
import os
import time


# catch non-integer population values (sometimes descriptive texts)
def int_population(population):
    try:
        pop = int(population)
    except Exception:
        pop = 0

    return pop


# translate population to popcat tag value
def population_to_popcat(population):
    pop = int_population(population)

    if pop == 0:
        popcat = "pc_0"
    elif pop < 1000:
        popcat = "pc_1"
    elif pop < 5000:
        popcat = "pc_1000"
    elif pop < 10000:
        popcat = "pc_5000"
    elif pop < 20000:
        popcat = "pc_10000"
    elif pop < 30000:
        popcat = "pc_20000"
    elif pop < 50000:
        popcat = "pc_30000"
    elif pop < 100000:
        popcat = "pc_50000"
    elif pop < 200000:
        popcat = "pc_100000"
    elif pop < 500000:
        popcat = "pc_200000"
    elif pop < 1000000:
        popcat = "pc_500000"
    elif pop >= 1000000:
        popcat = "pc_1000000"

    return popcat


# Create popcat tag for nodes by using population tag or data from popcat_data.
# The file to be read should only contain nodes with tag key "place"
class process_nodes(osmium.SimpleHandler):
    def __init__(self, writer, popcat_data):
        osmium.SimpleHandler.__init__(self)
        self.writer = writer
        self.popcat_data = popcat_data
        self.s = set(popcat_data[0])

    def node(self, n):
        # Default value
        popcat_value = "pc_0"

        # use a set for more speed
        if str(n.id) in self.s:
            i = self.popcat_data[0].index(str(n.id))
            popcat_value = self.popcat_data[1][i]

            if int(popcat_value) > 0 and int(popcat_value) < 1000:
                popcat_value = "pc_1"
            else:
                popcat_value = "pc_" + popcat_value

        # else: use population tag if available
        elif n.tags.get("population") is not None:
            population = n.tags.get("population")
            popcat_value = population_to_popcat(population)

        # else: use population tag from opengeodb
        elif n.tags.get("openGeoDB:population") is not None:
            population = n.tags.get("openGeoDB:population")
            popcat_value = population_to_popcat(population)

        # prepare and write popcat node
        tag_list = {}
        for k, v in n.tags:
            tag_list[k] = v
        tag_list["popcat"] = popcat_value

        popcat_node = n.replace(tags=tag_list)
        self.writer.add_node(popcat_node)


def run(file_in, map_, file_out):
    start_time = time.time()

    if os.path.exists(file_out):
        print("    File %s already exists." % file_out)
        return

    # filter places nodes
    tmp_file = file_out[:-3] + "o5m"
    cmd = ("osmfilter " + file_in + " "
           "--parameter-file=osmfilter_parameters/popcat_nodes.txt "
           "-o=" + tmp_file)
    os.system(cmd)

    # read popcat data an transpose and convert to list
    file_popcat = "popcat_peaks_saddles/PopCatFile4OAM.csv"
    f = open(file_popcat, mode="r", newline="\n")
    reader = csv.reader(f, delimiter=';')
    popcat_data = list(zip(*reader))
    f.close()

    if os.path.exists(file_out):
        os.remove(file_out)
    writer = osmium.SimpleWriter(file_out)

    pn = process_nodes(writer, popcat_data)
    pn.apply_file(tmp_file)
    os.remove(tmp_file)

    writer.close()

    print("    %s seconds" % round((time.time() - start_time), 1))
