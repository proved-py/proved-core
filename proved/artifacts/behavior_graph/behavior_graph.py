from networkx import DiGraph
from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys


class BehaviorGraph(DiGraph):
    """
    Class representing a behavior graph, a directed acyclic graph showing the precedence relationship between uncertain events.
    For more information refer to:
        Pegoraro, Marco, and Wil MP van der Aalst. "Mining uncertain event data in process mining." 2019 International Conference on Process Mining (ICPM). IEEE, 2019.
    """

    def __init__(self, trace, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=xes_keys.DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=xes_keys.DEFAULT_U_TIMESTAMP_MAX_KEY, u_missing_key=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        DiGraph.__init__(self)

        timestamps_list = []
        nodes_list = []
        edges_list = []

        # Creates all the nodes in the graph
        for i, event in enumerate(trace):
            if u_activity_key not in event:
                if u_missing_key not in event:
                    new_node = (i, frozenset((event[activity_key],)))
                else:
                    new_node = (i, frozenset((event[activity_key], None)))
            else:
                if u_missing_key not in event:
                    new_node = (i, frozenset(event[u_activity_key]['children']))
                else:
                    new_node = (i, frozenset(tuple(event[u_activity_key]['children']) + (None,)))

            nodes_list.append(new_node)

            # Fill in the timestamps list
            if u_timestamp_min_key not in event:
                timestamps_list.append((event[timestamp_key], new_node, 'CERTAIN'))
            else:
                timestamps_list.append((event[u_timestamp_min_key], new_node, 'LEFT'))
                timestamps_list.append((event[u_timestamp_max_key], new_node, 'RIGHT'))

        # Sort timestamps_list by first term of its elements
        timestamps_list.sort()

        # Adding the nodes to the graph object
        self.add_nodes_from(nodes_list)

        # Applies the sweeping algorithm to the sorted list
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
