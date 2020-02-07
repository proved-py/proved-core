from networkx import DiGraph
from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys


class BehaviorGraph(DiGraph):

    def __init__(self, trace, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY, u_timestamp_left=xes_keys.DEFAULT_U_TIMESTAMP_LEFT_KEY, u_timestamp_right=xes_keys.DEFAULT_U_TIMESTAMP_RIGHT_KEY, u_missing=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        DiGraph.__init__(self)

        timestamps_list = []
        nodes_list = []
        edges_list = []
        for i, event in enumerate(trace):
            if u_activity_key not in event:
                if u_missing not in event:
                    new_node = (i, frozenset(event[activity_key]))
                else:
                    new_node = (i, frozenset([event[activity_key], None]))
            else:
                if u_missing not in event:
                    new_node = (i, frozenset(event[u_activity_key]['children']))
                else:
                    new_node = (i, frozenset(event[u_activity_key]['children'] + [None]))

            nodes_list.append(new_node)

            # Fill in the timestamps list
            if u_timestamp_left not in event:
                timestamps_list.append((event[timestamp_key], new_node, 'CERTAIN'))
            else:
                timestamps_list.append((event[u_timestamp_left], new_node, 'LEFT'))
                timestamps_list.append((event[u_timestamp_right], new_node, 'RIGHT'))

        # Sort timestamps_list by first term of its elements
        timestamps_list.sort()

        # Adding the nodes to the graph object
        self.add_nodes_from(nodes_list)

        for i, timestamp1 in enumerate(timestamps_list):
            if timestamp1[2] != 'LEFT':
                for timestamp2 in timestamps_list[i + 1:]:
                    if timestamp2[2] == 'LEFT':
                        edges_list.append((timestamp1[1], timestamp2[1]))
                    if timestamp2[2] == 'CERTAIN':
                        edges_list.append((timestamp1[1], timestamp2[1]))
                        break
                    if timestamp2[2] == 'RIGHT':
                        if (timestamp1[1], timestamp2[1]) in edges_list:
                            break

        # Adding the edges to the graph object
        self.add_edges_from(edges_list)
