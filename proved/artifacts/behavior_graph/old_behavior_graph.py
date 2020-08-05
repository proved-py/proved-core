from networkx import DiGraph
from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys


def create_nodes_tuples(trace, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=xes_keys.DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=xes_keys.DEFAULT_U_TIMESTAMP_MAX_KEY, u_missing_key=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
    # TODO: test this
    nodes_list = []
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

        # Fill in the timestamps list
        if u_timestamp_min_key not in event:
            nodes_list.append((event[timestamp_key], new_node, 'C'))
        else:
            nodes_list.append((event[u_timestamp_min_key], new_node, 'L'))
            nodes_list.append((event[u_timestamp_max_key], new_node, 'R'))

    # Sort nodes_list by first term of its elements
    nodes_list.sort()

    # Returns a tuple of nodes and timestamp types sorted by timestamp
    return tuple((node, timestamp_type) for _, node, timestamp_type in nodes_list)


class BehaviorGraph(DiGraph):
    # TODO: test this
    """
    Class representing a behavior graph, a directed acyclic graph showing the precedence relationship between uncertain events.
    For more information refer to:
        Pegoraro, Marco, and Wil MP van der Aalst. "Mining uncertain event data in process mining." 2019 International Conference on Process Mining (ICPM). IEEE, 2019.
    """

    def __init__(self, trace, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=xes_keys.DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=xes_keys.DEFAULT_U_TIMESTAMP_MAX_KEY, u_missing_key=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        super().__init__(self)

        node_tuples = create_nodes_tuples(trace, activity_key, timestamp_key, u_timestamp_min_key, u_timestamp_max_key, u_missing_key, u_activity_key)
        edges_list = []

        # Adding the nodes to the graph object
        self.add_nodes_from([node for node, _ in node_tuples])

        # Applies the sweeping algorithm to the sorted list
        # TODO: there are still bugs in the case timestamps coincide!
        for i, node_tuple1 in enumerate(node_tuples):
            node1, type1 = node_tuple1
            if type1 != 'L':
                for j, node_tuple2 in enumerate(node_tuples[i + 1:]):
                    node2, type2 = node_tuple2
                    if type2 == 'L':
                        edges_list.append((node1, node2))
                    if type2 == 'C':
                        edges_list.append((node1, node2))
                        break
                        # if j + 1 < len(timestamps_list) and timestamp2[0] < timestamps_list[j + 1][0]:
                        #     break
                    if type2 == 'R':
                        if (node1, node2) in edges_list:
                            break
                            # if j + 1 < len(timestamps_list) and timestamp2[0] < timestamps_list[j + 1][0]:
                            #     break

        # Adding the edges to the graph object
        self.add_edges_from(edges_list)
