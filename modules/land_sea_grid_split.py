import osmium
import os

# parameters to calculate the grid size for each polygon
size_x_min = 0.034
size_y_min = 0.027
size_x_max = 0.63
size_y_max = 0.5
density_min = 1000
density_max = 25000
overlap = 0.0001

# don't split polygons that have less than skip_limit nodes
skip_limit = 500

start_node_id = -20000000000
start_way_id = -20000000000


# Process all polygons (ways). Small polygons are skipped and passed to the
# writer unchanged.
class collect_data(osmium.SimpleHandler):
    def __init__(self, writer, start_node_id, start_way_id):
        osmium.SimpleHandler.__init__(self)
        # dict of all nodes in the osm input file with their coordinates
        # newly calculated nodes are also added
        # {"node_id1": point_object, "node_id2": point_object, ...}
        self.node_data = {}

        self.writer = writer
        self.i_n = start_node_id
        self.i_w = start_way_id

    def way(self, w):
        # Input file is not osm-sorted, nodes for each land polygon are located
        # right before the land polygon way. Therefore, len(self.node_data) at
        # this time is the same as len(w.nodes)
        length = len(self.node_data)
        if length > skip_limit:

            refs = []
            refs.extend(n.ref for n in w.nodes)
            poly = polygon_object(w.id, refs, length, self.node_data)

            # create a grid overlapping the polygon
            self.i_n = poly.create_grid(self.node_data, self.i_n)

            # process each grid box: collect nodes inside --> clip poly
            # segments --> create new land polygons
            for row in poly.grid:
                for box in row:
                    self.i_n = box.collect_nodes_inside(poly, self.node_data,
                                                        self.i_n)

                    if False in box.nodes_inside:
                        poly.is_island_in_box = False
                    else:
                        poly.is_island_in_box = True

                    if not poly.is_island_in_box:
                        box.store_poly_segments(poly)
                        self.i_n = box.clip_poly_segments(poly, self.node_data,
                                                          self.i_n)

                    box.create_land_polygons(poly, self.node_data,
                                             self.writer)

            # "empty" grid boxes completely inside a poly do not help to speed
            # up mapsforge-mapwriter. combine some of these boxes to larger
            # boxes.
            poly.combine_boxes_inside_poly(self.node_data)

            for sp in poly.split_polygons:
                write_land_way(self.writer, self.i_w, sp.nids)
                self.i_w = self.i_w + 1

        else:
            write_land_way(self.writer, w.id, w.nodes)

        for n in self.node_data:
            write_node(self.writer, n, self.node_data[n])

        # clear nodes dict for next land polygon/way
        self.node_data = {}

    def node(self, n):
        self.node_data[n.id] = point_object(n.location.lon, n.location.lat)


def max_lon(node_list, node_data):
    return max(node_data[n].x for n in node_list)


def min_lon(node_list, node_data):
    return min(node_data[n].x for n in node_list)


def max_lat(node_list, node_data):
    return max(node_data[n].y for n in node_list)


def min_lat(node_list, node_data):
    return min(node_data[n].y for n in node_list)


class polygon_object:
    def __init__(self, pid, refs, length, node_data):
        self.pid: pid
        self.nids = refs
        self.length = length
        self.is_island_in_box = False

        # list of split polygons created by grid split from this polygon
        self.split_polygons = []

        # nested list of grid-boxes:
        # [row1 [box1, box2, ...], row2 [box1, box2, ...]
        self.grid = []

        self.ma_lo_x = max_lon(refs, node_data)+0.001
        self.mi_lo_x = min_lon(refs, node_data)-0.001
        self.ma_la_y = max_lat(refs, node_data)+0.001
        self.mi_la_y = min_lat(refs, node_data)-0.001

        # ratio square_area / number_of_nodes
        self.density = self.density(self.ma_lo_x, self.mi_lo_x,
                                    self.ma_la_y, self.mi_la_y)

    def density(self, ma_lo_x, mi_lo_x, ma_la_y, mi_la_y):
        d = self.length / abs((ma_lo_x - mi_lo_x) * (ma_la_y - mi_la_y))
        if d < density_min:
            return density_min
        if d > density_max:
            return density_max
        return d

    # calculate delta_x and delta_y for grid box size
    def __dx_dy(self):
        dx = ((size_x_max - size_x_min) / (density_min - density_max)
              * (self.density - density_min) + size_x_max)
        dy = ((size_y_max - size_y_min) / (density_min - density_max)
              * (self.density - density_min) + size_y_max)
        return dx, dy

    # create an overlapping grid covering the whole polygon
    def create_grid(self, node_data, i_n):
        size_x, size_y = self.__dx_dy()

        nx = int((self.ma_lo_x - self.mi_lo_x)/size_x+1)
        ny = int((self.ma_la_y - self.mi_la_y)/size_y+1)
        dx = (self.ma_lo_x - self.mi_lo_x) / nx
        dy = (self.ma_la_y - self.mi_la_y) / ny

        for y in range(0, ny):
            row = []
            for x in range(0, nx):
                # calculate box corner coordinates
                c1 = corner_point_object(self.mi_lo_x + dx * x - overlap,
                                         self.ma_la_y - dy * y + overlap)
                c2 = corner_point_object(self.mi_lo_x + dx * (x + 1) + overlap,
                                         self.ma_la_y - dy * y + overlap)
                c3 = corner_point_object(self.mi_lo_x + dx * (x + 1) + overlap,
                                         self.ma_la_y - dy * (y + 1) - overlap)
                c4 = corner_point_object(self.mi_lo_x + dx * x - overlap,
                                         self.ma_la_y - dy * (y + 1) - overlap)

                box = box_object(x, y, [c1, c2, c3, c4])
                i_n = box.det_corner_locations(i_n, self, node_data)

                # add box to grid
                row.append(box)

            self.grid.append(row)

        return i_n

    def add_split_poly(self, split_poly, completely_inside, x, x_end, y):
        sp = split_polygon_object(split_poly, completely_inside, x, x_end, y)
        self.split_polygons.append(sp)

    # see point_in_poly
    def __cross_product_test(self, A_x, A_y, B_x, B_y, C_x, C_y):
        if A_y == B_y == C_y:
            if B_x <= A_x <= C_x or C_x <= A_x <= B_x:
                return 0
            else:
                return 1
        if A_y == B_y and A_x == B_x:
            return 0
        if B_y > C_y:
            temp_x = B_x
            temp_y = B_y
            B_x = C_x
            B_y = C_y
            C_x = temp_x
            C_y = temp_y
        if A_y <= B_y or A_y > C_y:
            return 1
        delta = (B_x - A_x) * (C_y - A_y) - (B_y - A_y) * (C_x - A_x)
        if delta > 0:
            return -1
        elif delta < 0:
            return 1
        else:
            return 0

    # Jordan point-in polygon-test
    # return values: +1: point is inside poly, -1 point is outside poly,
    # 0 point is on border/edge of poly
    def point_in_poly(self, Q, node_data):
        t = -1
        for n in range(len(self.nids)-1):
            t *= self.__cross_product_test(Q.x, Q.y,
                                           node_data[self.nids[n]].x,
                                           node_data[self.nids[n]].y,
                                           node_data[self.nids[n+1]].x,
                                           node_data[self.nids[n+1]].y)
            if t == 0:
                break
        return t

    # function calls point_in_poly but with an additonal check to improve speed
    def point_in_poly_check(self, Q, node_data):
        if not self.mi_lo_x <= Q.x <= self.ma_lo_x:
            return -1
        elif not self.mi_la_y <= Q.y <= self.ma_la_y:
            return -1
        return self.point_in_poly(Q, node_data)

    # Return True if center of P1/P2 is inside the poly, else False.
    def center_in_poly(self, P1, P2, node_data):
        center = point_object((P1.x + P2.x)/2, (P1.y + P2.y)/2)
        erg = self.point_in_poly(center, node_data)
        if erg > 0:
            return True
        else:
            return False

    # Combine some split polygons that represent four-node-grid boxes and which
    # are completely inside the polygon.
    def combine_boxes_inside_poly(self, node_data):
        prev_x_start = -1
        prev_x_end = -1
        prev_y = -1
        p = self.split_polygons
        for i_sp, sp in enumerate(p):

            # list of indices of candidate split polygons to combine with other
            # split polygons
            combine_list = []

            # list of nids defining a polygon that combines boxes completely
            # inside the polygon
            new_poly = []

            if sp.completely_inside:
                combine_list.append(i_sp)
                x_start = sp.x
                y = sp.y

                # check for more split polygons to combine in the same row
                for sp2 in range(i_sp+1, len(p)):
                    if (p[sp2].is_next_to(p[sp2-1])
                            and p[sp2].completely_inside):
                        combine_list.append(sp2)
                    else:
                        break

                x_end = p[combine_list[-1]].x_end

                # check if union with last created combined split polygon
                # (p[-1]) is possible
                if (prev_x_start == x_start
                        and prev_x_end == x_end
                        and (prev_y+1) == p[combine_list[0]].y):

                    nid1 = p[-1].nids[0]
                    nid2 = p[-1].nids[1]
                    nid3 = p[combine_list[-1]].nids[2]
                    nid4 = p[combine_list[0]].nids[3]

                    # add the previous poly with index len(p)-1 to combine list
                    # so that the split poly and its nodes will be deleted
                    # later
                    combine_list.insert(0, len(p)-1)

                # do not combine with previous poly
                else:
                    nid1 = p[combine_list[0]].nids[0]
                    nid2 = p[combine_list[-1]].nids[1]
                    nid3 = p[combine_list[-1]].nids[2]
                    nid4 = p[combine_list[0]].nids[3]

                new_poly.extend([nid1, nid2, nid3, nid4, nid1])

                # prepare for next run, remember size and position of previous
                # combined boxes/polys
                prev_x_start = sp.x
                prev_x_end = x_end
                prev_y = sp.y

                # skip if there is nothing to combine
                if new_poly == []:
                    continue

                self.add_split_poly(new_poly, True, x_start, x_end, y)

                # delete nodes that are not necessary any more
                node_del_set = set()
                for c in combine_list:
                    for n in p[c].nids:
                        if n not in new_poly:
                            node_del_set.add(n)
                for nd in node_del_set:
                    del node_data[nd]

                # remove unnecessary split polygons
                for pd in sorted(combine_list, reverse=True):
                    del self.split_polygons[pd]


class split_polygon_object:
    def __init__(self, nids, completely_inside, x, x_end, y):
        # osm node ids of split polygon
        self.nids = nids
        # True if the split polygon is completely inside the parent polygon
        self.completely_inside = completely_inside
        # grid x value of the box in which the split polygon was created
        self.x = x
        # grid x value of the last box included in this split polygon (in
        # case it has been combined with other split polygons)
        self.x_end = x_end
        # grid y value of the box in which the split polygon was created
        self.y = y

    def is_next_to(self, split_polygon):
        if (self.x == split_polygon.x+1 and self.y == split_polygon.y):
            return True
        else:
            return False


class point_object:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class corner_point_object(point_object):
    def __init__(self, x, y):
        super(self.__class__, self).__init__(x, y)
        # True if corner point has already been used in a poly segment
        self.used = False
        # box corner location: -1 outside poly, 0 poly border, 1 inside poly
        self.loc = -2


class box_object:
    def __init__(self, x, y, corner_points):
        # x, y position in grid
        self.x = x
        self.y = y
        # node id of box corners
        self.cn = []
        # box corner points
        self.cp = corner_points
        # Boolean list with same length as the current polygons's node list to
        # store which poly nodes are inside the box. Needed during construction
        # of self.poly_segments
        self.nodes_inside = []
        # poly segments (node ids) inside the box
        self.poly_segments = []
        # list of poly nodes on box border/edge (nodes where polygon segments
        # inside the box start), per border/edge 1-4
        self.bnpb = [[], [], [], []]
        # length of bnpb, stored for speed improvement
        self.bnpb_len = [0, 0, 0, 0]
        # all poly nodes on box border/edges (sorted, see function
        # clip_poly_segments)
        self.bn = []
        # store whether box border/edge node has been used in a polygon
        self.bnx = []
        # list of poly segments inside of box, segments start at bn, per
        # border/edge 1-4
        self.bwpb = [[], [], [], []]
        # all poly segments inside box (sorted, see function
        # clip_poly_segments)
        self.bw = []

    # Check all box corners: inside/on border/outside poly?, store result and
    # add osm id to global node data if corner is inside the poly.
    def det_corner_locations(self, i_n, poly, node_data):
        for P in self.cp:
            P.loc = poly.point_in_poly_check(P, node_data)
            self.cn.append(i_n)

            if P.loc == 1:
                node_data[i_n] = P
            i_n = i_n + 1

        return i_n

    # Return the current box edge 1...4 based on the index i of a border point
    # in box.bn.
    def current_edge(self, i):
        sum_len = 0
        for i_b, b_len in enumerate(self.bnpb_len):
            sum_len += b_len
            if i <= sum_len-1:
                return i_b + 1

    # Return the next edge index (1...4) relative to the current edge.
    def next_edge(self, edge):
        if edge == 4:
            return 1
        else:
            return edge + 1

    # Return the node id of the next corner node relative to the current edge.
    def next_cornder_node(self, edge):
        if edge < 4:
            return self.cn[edge]
        else:
            return self.cn[0]

    # Return the node id of the next border/edge node or the next corner node
    # (if there are no more bp on the current edge).
    def next_bp(self, i):
        edge = self.current_edge(i)
        node_count = self.node_count_up_to_current_edge(edge)

        # there is at least one more bp on this edge
        if i < (node_count-1):
            return self.bn[i+1]
        else:
            return self.next_cornder_node(edge)

    # Return the sum of border/edge nodes from edge/border 1 up to "edge".
    def node_count_up_to_current_edge(self, edge):
        node_count = 0
        for e in range(edge):
            node_count += self.bnpb_len[e]
        return node_count

    # Same as next_bp, but check whether bp/corner has already been used for a
    # split polygon.
    def next_unused_bp(self, i):
        edge = self.current_edge(i)
        while True:
            node_count = self.node_count_up_to_current_edge(edge)

            # there is at least one more bp on this edge
            while i < (node_count-1):
                if not self.bnx[i+1]:
                    return self.bn[i+1]
                i += 1

            # no more nodes on this edge: try corner node
            if edge < 4 and not self.cp[edge].used:
                return self.cn[edge]
            elif edge == 4 and not self.cp[0].used:
                return self.cn[0]

            # current corner has also been used: try next edge
            edge = self.next_edge(edge)
            if edge == 1:
                i = -1

    # Same as next_u_bp but without corners.
    def next_u_bp_wo_corners(self, i):
        while self.bnx[i+1] is True:
            i += 1
        return self.bn[i+1], i+1

    # Check if p is in box. Return True if Q is in box, else False.
    # For nodes on the border/edge, return value is False.
    def p_in_box(self, Q):
        if not self.cp[0].x < Q.x < self.cp[1].x:
            return False
        elif not self.cp[2].y < Q.y < self.cp[1].y:
            return False
        else:
            return True

    # Return box corner coordinates based on corner index i (1...4).
    def corner_coords(self, i):
        return self.cp[i-1]

    # Return box corner coordinates based on corner index i (1...4) for
    # the next corner after i.
    def next_corner_coords(self, i):
        if i == 4:
            return self.corner_coords(1)
        else:
            return self.corner_coords(i+1)

    # Identify and store node sequences inside the box.
    # Also consider if a poly segment crosses box borders with no nodes inside.
    def collect_nodes_inside(self, poly, node_data, i_n):

        # Store booelan list for polygon nodes inside the box.
        for n in poly.nids:
            if self.p_in_box(node_data[n]):
                self.nodes_inside.append(True)
            else:
                self.nodes_inside.append(False)

        # Ways crossing corners without nodes in the box should not be
        # missed. Check wheter line between two poly nodes outside the box
        # intersects box borders.
        # If this case is detected, a new node inside the box will be inserted.
        i = 0
        while (i < len(self.nodes_inside)-1):

            if not self.nodes_inside[i] and not self.nodes_inside[i+1]:
                intersections = []
                W1 = node_data[poly.nids[i]]
                W2 = node_data[poly.nids[i+1]]

                for e in range(1, 5):
                    P1 = self.corner_coords(e)
                    P2 = self.next_corner_coords(e)
                    erg = intersection_check(P1, P2, W1, W2)
                    if erg is not None:
                        intersections.append(erg)

                        # stop if two intersection points have been detected
                        if len(intersections) == 2:
                            # Any line between two points outside of the box
                            # can either cross two edges or touch all four
                            # edges (diagonal line).
                            # Insert a new node in poly to not miss these
                            # sections later
                            x = (intersections[0].x + intersections[1].x)/2
                            y = (intersections[0].y + intersections[1].y)/2
                            new_node = point_object(x, y)

                            poly.nids.insert(i+1, i_n)
                            self.nodes_inside.insert(i+1, True)
                            node_data[i_n] = new_node
                            i_n = i_n + 1
                            i += 1

                            break
            i += 1

        return i_n

    # Store consecutive poly segments that are inside the box, plus
    # one node before and one after.
    def store_poly_segments(self, poly):
        start = -1
        temp_list = []
        nodes_inside_len = len(self.nodes_inside)

        for i, n in enumerate(self.nodes_inside):

            # start of node sequence in box
            if n is True and start == -1:
                start = i

            # end of node sequence in box or end of polygon
            if (n is False or i == nodes_inside_len-1) and start != -1:
                # node sequence startet at 0 but real start might be earlier
                if start == 0:
                    # how long de we need to go back to the real start?
                    for ir, nr in enumerate(reversed(self.nodes_inside)):
                        if nr is False:
                            break
                    temp_list.extend(poly.nids[-ir-1:-1])
                    start = 1

                if n is False and i == nodes_inside_len-1:
                    temp_list.extend(poly.nids[start-1:i+1])
                    self.poly_segments.append(temp_list)

                # the following case is not added to
                # box.poly_segments, because: if n==True and
                # i==last_node_of_way, then this will be catched by
                # the case "start == 0" above because first and
                # last node are the same for closed land polygons
                elif n is True and i == nodes_inside_len-1:
                    temp_list = []
                else:
                    # add polygon sequence to box
                    temp_list.extend(poly.nids[start-1:i+1])
                    self.poly_segments.append(temp_list)

                temp_list = []
                start = -1

    # For all node sequences of a box, calculate the intersection
    # points with the box borders/edges and clip the node sequences to
    # begin/end at the box border/edge.
    # For each box, store a list of intersection points on the
    # box borders (same order as list of node sequences).
    def clip_poly_segments(self, poly, node_data, i_n):

        # temporary list of indices to link self.bnpb <-> self.bwpb
        seg_index_per_edge = [[] for i in range(4)]

        # clip all poly segments to start at a box border and store start
        # and end node in bnpb (border nodes per border)
        for edge in range(1, 5):
            P1 = self.corner_coords(edge)
            P2 = self.next_corner_coords(edge)

            # loop throug all node sequences in the box:
            for i_poly, poly_seg in enumerate(self.poly_segments):

                # does the beginning or end of the node sequence
                # intersect the current border?
                W1 = node_data[poly_seg[0]]
                W2 = node_data[poly_seg[1]]
                erg = intersection(P1, P2, W1, W2)
                if erg is not None:
                    # Line poly_seg[0] --> poly_seg[1] intersects box
                    # border. Replace poly_seg[0] with a new node on the border
                    # (with node-id i_n).
                    poly_seg[0] = i_n
                    node_data[i_n] = erg
                    self.bnpb[edge-1].append(i_n)
                    seg_index_per_edge[edge-1].append(i_poly)
                    i_n = i_n + 1

                W1 = node_data[poly_seg[-1]]
                W2 = node_data[poly_seg[-2]]
                erg = intersection(P1, P2, W1, W2)
                if erg is not None:
                    # Line poly_seg[-1] --> poly_seg[-2] intersects box
                    # border. Replace poly_seg[-1] with a new node on the
                    # border (with node-id i_n).
                    poly_seg[-1] = i_n
                    node_data[i_n] = erg
                    self.bnpb[edge-1].append(i_n)
                    # negative i_poly will lead to inverse node sequence being
                    # stored in self.bwpb
                    seg_index_per_edge[edge-1].append(-i_poly)
                    i_n = i_n + 1

        # build bwpb (border ways per edge) after each poly segment has been
        # fully clipped
        for e, edge in enumerate(seg_index_per_edge):
            for i in edge:
                if i >= 0:
                    self.bwpb[e].append(self.poly_segments[i])
                else:
                    # append reveresed node_list, as polys segments should
                    # always start at the current edge
                    self.bwpb[e].append(self.poly_segments[i][::-1])

        # Sort the list of intersection points, border-ways and border
        # nodes in the same order.
        # Then combine the single lists to one combined list for all box
        # corners
        # border 1 / self.bnpb[0]: sort from min_x to max_x
        if self.bnpb[0] != []:
            x = [node_data[i].x for i in self.bnpb[0]]
            x, self.bwpb[0], self.bnpb[0] = zip(
                *sorted(zip(x, self.bwpb[0], self.bnpb[0])))

        # border2 / self.bnpb[1]: sort from max_y to min_y
        if self.bnpb[1] != []:
            y = [node_data[i].y for i in self.bnpb[1]]
            y, self.bwpb[1], self.bnpb[1] = zip(
                *sorted(zip(y, self.bwpb[1], self.bnpb[1]), reverse=True))

        # border3 / self.bnpb[2]: sort from max_x to min_x
        if self.bnpb[2] != []:
            x = [node_data[i].x for i in self.bnpb[2]]
            x, self.bwpb[2], self.bnpb[2] = zip(
                *sorted(zip(x, self.bwpb[2], self.bnpb[2]), reverse=True))

        # border 4 / self.bnpb[3]: sort from min_y to max_y
        if self.bnpb[3] != []:
            y = [node_data[i].y for i in self.bnpb[3]]
            y, self.bwpb[3], self.bnpb[3] = zip(
                *sorted(zip(y, self.bwpb[3], self.bnpb[3])))

        for n in range(0, 4):
            self.bn.extend(self.bnpb[n])
            self.bw.extend(self.bwpb[n])
            self.bnpb_len[n] = len(self.bnpb[n])

        # list to store whether border point has already been processed
        self.bnx = [False] * len(self.bn)

        # delete unneeded data
        self.poly_segments = []

        return i_n

    # Create land polygons.
    # Process all nodes on the box borders in clockwise direction
    # (edge 1 -> edge 2 -> edge 3 -> edge 4). Box border nodes are the nodes
    # where poly segments inside the box (box.bw) start.
    def create_land_polygons(self, poly, node_data, writer):
        while False in self.bnx:
            new_poly = []
            i = -1

            # next unused border point, don't consider corners
            next_u_bp, i = self.next_u_bp_wo_corners(i)
            i_start = i

            # start land polygon with first point
            new_poly.append(next_u_bp)

            # differenciate case #1 / case #2 based on the location of the
            # point in the middle between poly start point (next_u_bp) and
            # bp_next
            coord_start = node_data[next_u_bp]
            bp_next = self.next_bp(i)
            if bp_next in self.bn:
                coord_bp_next = node_data[bp_next]
            elif bp_next in self.cn:
                coord_bp_next = self.cp[self.cn.index(bp_next)]

            # case #1: land polygon continues on the edge/border
            # of the box
            if poly.center_in_poly(coord_start, coord_bp_next, node_data):

                while True:
                    i, next_u_bp = self.follow_border(i, new_poly)
                    i = self.follow_poly_segment(i, new_poly)

                    # check whether the land polygon is finished/closed
                    if new_poly[-1] == new_poly[0]:
                        poly.add_split_poly(new_poly, False, self.x, self.x,
                                            self.y)
                        break

            # case 2: land polygon continues towards the inner of
            # the box
            else:
                while True:
                    i = self.follow_poly_segment(i, new_poly)

                    # first node of new_poly needs to be set unused, otherwise
                    # follow_border can fail
                    if i_start != -1:
                        self.bnx[i_start] = False
                        i_start = -1

                    i, next_u_bp = self.follow_border(i, new_poly)

                    # check whether the land polygon can be finished/closed
                    if next_u_bp == new_poly[0]:
                        # close polygon
                        new_poly.append(next_u_bp)
                        self.bnx[i] = True

                        poly.add_split_poly(new_poly, False, self.x, self.x,
                                            self.y)
                        break

        # special case #1: all box corners inside poly, no intersections, box
        # completely inside polygon
        if self.bw == []:
            if (self.cp[0].loc >= 0 and self.cp[1].loc >= 0
                    and self.cp[2].loc >= 0 and self.cp[3].loc >= 0):
                node_list = self.cn
                node_list.append(self.cn[0])
                poly.add_split_poly(node_list, True, self.x, self.x, self.y)

        # special case #2: poly compoletely inside a box
        if poly.split_polygons == [] and poly.is_island_in_box:
            poly.add_split_poly(poly.nids, False, self.x, self.x, self.y)

    # Follow the polygon along the box border to the next not-yet-used border
    # point. include box corners if necessary. Return values are index and
    # node id of the next not-yet-used border point.
    def follow_border(self, index_last_border_point, new_poly):
        next_u_bp = self.next_unused_bp(index_last_border_point)
        while next_u_bp in self.cn:
            new_poly.append(next_u_bp)
            self.cp[self.cn.index(next_u_bp)].used = True
            next_u_bp = self.next_unused_bp(index_last_border_point)
        i = self.bn.index(next_u_bp)

        return i, next_u_bp

    # Follow poly segment inside the box. Return border node index i
    # correspondig to where the poly segment hits the box border.
    def follow_poly_segment(self, i, new_poly):
        # border way bw[i] that starts at bn[i]
        new_poly.extend(self.bw[i])
        self.bnx[i] = True

        node_id_end = self.bw[i][-1]
        i = self.bn.index(node_id_end)
        self.bnx[i] = True

        return i


# Function calls intersection() but checks first if an intersection is possible
# to improve speed.
def intersection_check(P1, P2, Q1, Q2):
    if Q1.x < P1.x and Q1.x < P2.x and Q2.x < P1.x and Q2.x < P2.x:
        return None
    elif Q1.x > P1.x and Q1.x > P2.x and Q2.x > P1.x and Q2.x > P2.x:
        return None
    elif Q1.y < P1.y and Q1.y < P2.y and Q2.y < P1.y and Q2.y < P2.y:
        return None
    elif Q1.y > P1.y and Q1.y > P2.y and Q2.y > P1.y and Q2.y > P2.y:
        return None
    else:
        return intersection(P1, P2, Q1, Q2)


# Calculate the intersection between two line segments (defined by P1/2 and
# Q1/Q2).
# Return value is a point_object with x/y of the intersection point. If there
# there is no intersection, return None.
def intersection(P1, P2, Q1, Q2):
    # y = m_P * x + b_P
    # y = m_Q * x + b_Q

    # neither P nor Q is vertical
    if P1.x != P2.x and Q1.x != Q2.x:
        m_P = (P2.y - P1.y) / (P2.x - P1.x)
        m_Q = (Q2.y - Q1.y) / (Q2.x - Q1.x)
        b_P = P1.y - m_P * P1.x
        b_Q = Q1.y - m_Q * Q1.x

        # parallel
        if m_P == m_Q:
            return None

        # m_P * x + b_P = m_Q * x + b_Q
        x_SP = (b_Q - b_P) / (m_P - m_Q)
        y_SP = m_P * x_SP + b_P

        # check if intersectin is outside line segments
        if x_SP < min(P1.x, P2.x) or x_SP > max(P1.x, P2.x):
            return None
        elif x_SP < min(Q1.x, Q2.x) or x_SP > max(Q1.x, Q2.x):
            return None
        else:
            return point_object(x_SP, y_SP)

    # P is vertical
    elif P1.x == P2.x and Q1.x != Q2.x:
        m_Q = (Q2.y - Q1.y) / (Q2.x - Q1.x)
        b_Q = Q1.y - m_Q * Q1.x
        x_SP = P1.x
        y_SP = m_Q * x_SP + b_Q

        # check if intersectin is outside line segments
        if x_SP < min(Q1.x, Q2.x) or x_SP > max(Q1.x, Q2.x):
            return None
        elif y_SP < min(P1.y, P2.y) or y_SP > max(P1.y, P2.y):
            return None
        else:
            return point_object(x_SP, y_SP)

    # Q is vertical
    elif Q1.x == Q2.x and P1.x != P2.x:
        m_P = (P2.y - P1.y) / (P2.x - P1.x)
        b_P = P1.y - m_P * P1.x
        x_SP = Q1.x
        y_SP = m_P * x_SP + b_P

        # check if intersectin is outside line segments
        if x_SP < min(P1.x, P2.x) or x_SP > max(P1.x, P2.x):
            return None
        elif y_SP < min(Q1.y, Q2.y) or y_SP > max(Q1.y, Q2.y):
            return None
        else:
            return point_object(x_SP, y_SP)

    # both are vertical
    elif Q1.x == Q2.x and P1.x == P2.x:
        return None


def write_land_way(writer, i, n):
    tl = {}
    tl["layer"] = "-5"
    tl["natural"] = "nosea"
    write_way(writer, i, n, tl)


def write_way(writer, i, n, tl):
    w = osmium.osm.Way("").replace(id=i, nodes=n, version=1, visible=True,
                                   changeset=1,
                                   timestamp="1970-01-01T00:59:59Z", uid=1,
                                   user="", tags=tl)
    writer.add_way(w)


def write_node(writer, i, loc):
    n = osmium.osm.Node("").replace(id=int(i), location=[loc.x, loc.y],
                                    version=1, visible=True, changeset=1,
                                    timestamp="1970-01-01T00:59:59Z",
                                    uid=1, user="", tags=[])
    writer.add_node(n)


def run(file_in, file_out):
    if os.path.exists(file_out):
        os.remove(file_out)
    writer = osmium.SimpleWriter(file_out)

    cd = collect_data(writer, start_node_id, start_way_id)
    cd.apply_file(file_in)

    writer.close()
