import osmium
import os


# create a ref tag with a maximum of seven characters from ref_source
def create_ref(ref_source):
    capital_letters = ''.join([c for c in ref_source if c.isupper()])
    numbers = ''.join([c for c in ref_source if c.isnumeric()])
    ref_temp = ref_source.replace(" ", "")

    # if ref_source contains only capital letters and/or numbers: use
    # the first seven characters as REF. Example:
    # ref_source = "ABCDEF7X"
    # ref = "ABCDEF7"
    if len(ref_temp) == len(capital_letters) + len(numbers):
        ref = ref_temp[0:7]

    # else if ref_source only has one capital letter: use a maximum of seven
    # numbers as ref an fill up the ref-tag with the first letters. Example:
    # ref_source = "Fernwanderweg 71"
    # ref = "Fernw71"
    elif len(capital_letters) == 1:
        ref = ref_temp[0:7-min(len(numbers), 7)]
        ref += numbers[0:min(len(numbers), 7)]

    # else use the first seven capital letters/numbers as ref. Example:
    # ref_source = "FernWanderWeg 1234567"
    # ref = "FWW1234"
    else:
        ref = ''.join([c for c in ref_source if c.isnumeric() or c.isupper()])
        ref = ref[0:7]

    return ref


# read all relations and adjust / create ref tag
# all ways and nodes are passed to the writer unchanged
class process_route_refs(osmium.SimpleHandler):
    def __init__(self, writer):
        osmium.SimpleHandler.__init__(self)
        self.writer = writer

    def relation(self, r):
        ref_temp = r.tags.get("ref", "")

        # case 1: relation has a ref tag: limit it to seven characters
        if ref_temp != "":
            ref = ref_temp

            # limit length to 7 characters
            if len(ref_temp) > 7:
                ref = ref.replace(" ", "")
            if len(ref_temp) > 7:
                ref = create_ref(ref)

        # case 2: relation has no ref tag: use create_ref() to build a ref tag
        # from the name tag
        elif r.tags.get("name") is not None:
            ref = create_ref(r.tags.get("name"))

        # case 3: no ref
        else:
            ref = ""

        # add ref tag to tag list and pass relation to the writer
        tag_list = {}
        for k, v in r.tags:
            tag_list[k] = v
        tag_list["ref"] = ref
        rel = r.replace(tags=tag_list)
        self.writer.add_relation(rel)

    def way(self, w):
        self.writer.add_way(w)

    def node(self, n):
        self.writer.add_node(n)


def run(file_in, file_out):
    if os.path.exists(file_out):
        os.remove(file_out)
    writer = osmium.SimpleWriter(file_out)

    prr = process_route_refs(writer)
    prr.apply_file(file_in)
    writer.close()
