import operator

from networkx import DiGraph
from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY

from proved.xes_keys import DEFAULT_U_CONTINUOUS_STRONG, DEFAULT_U_TIMESTAMP_MIN_KEY, DEFAULT_U_TIMESTAMP_MAX_KEY, DEFAULT_U_DENSITY_FUNCTION_KEY, DEFAULT_U_NAME_KEY, DEFAULT_U_TIMESTAMP_KEY, DEFAULT_U_INDETERMINACY_KEY


def create_nodes_tuples(trace, activity_key=DEFAULT_NAME_KEY, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_continuous_strong=DEFAULT_U_CONTINUOUS_STRONG, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY, u_function_key=DEFAULT_U_DENSITY_FUNCTION_KEY, u_activity_key=DEFAULT_U_NAME_KEY, u_timestamp_key=DEFAULT_U_TIMESTAMP_KEY, u_indeterminacy_key=DEFAULT_U_INDETERMINACY_KEY):
    # Timestamp type: False is 'minimum', True is 'maximum'
    nodes_tuples = []
    for i, event in enumerate(trace):
        if u_activity_key not in event:
            if u_indeterminacy_key not in event:
                # If we do not have uncertainty on activities and the event is not indeterminate, we create a node with an event identifier and a set that only contains the activity label
                new_node = (i, frozenset((event[activity_key],)))
            else:
                # If we do not have uncertainty on activities and the event is indeterminate, we create a node with an event identifier and a set that contains the activity label and a None object (to signify indeterminacy)
                new_node = (i, frozenset((event[activity_key], None)))
        else:
            if u_indeterminacy_key not in event:
                # If we have uncertainty on activities and the event is not indeterminate, we create a node with an event identifier and a set that contains all possible activity labels
                # new_node = (i, frozenset(event[u_activity_key]['children']))
                new_node = (i, frozenset(event[u_activity_key]['children'].keys()))
            else:
                # If we have uncertainty on activities and the event is indeterminate, we create a node with an event identifier and a set that contains all possible activity labels, plus a None object
                # new_node = (i, frozenset(tuple(event[u_activity_key]['children']) + (None,)))
                new_node = (i, frozenset(tuple(event[u_activity_key]['children'].keys()) + (None,)))

        # Fill in the timestamps list
        # TODO: WARNING, only works on strongly uncertain timestamps
        if u_timestamp_key not in event:
            nodes_tuples.append((event[timestamp_key], new_node, False))
            nodes_tuples.append((event[timestamp_key], new_node, True))  # TODO: check if adding a tiny timedelta is necessary here
        elif event[u_timestamp_key]['value'] == u_continuous_strong:
            nodes_tuples.append((event[u_timestamp_key]['children'][u_timestamp_min_key], new_node, False))
            nodes_tuples.append((event[u_timestamp_key]['children'][u_timestamp_max_key], new_node, True))   # TODO: check if adding a tiny timedelta is necessary here (if the two timestamps are equal)
        else:  # Uncertain timestamp is weak
            pass  # TODO, this will need a helper function in a utils file

    # Sort nodes_tuples by first term of its elements and by type of timestamp
    nodes_tuples.sort(key=operator.itemgetter(0, 2))

    # Returns a tuple of nodes and timestamp types sorted by timestamp
    return tuple((node, timestamp_type) for _, node, timestamp_type in nodes_tuples)


class BehaviorGraph(DiGraph):
    """
    Class representing a behavior graph, a directed acyclic graph showing the precedence relationship between uncertain events.
    For more information refer to:
        Pegoraro, Marco, and Wil MP van der Aalst. "Mining uncertain event data in process mining." 2019 International Conference on Process Mining (ICPM). IEEE, 2019.
    """

    def __init__(self, trace, activity_key=DEFAULT_NAME_KEY, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY, u_missing_key=DEFAULT_U_INDETERMINACY_KEY, u_activity_key=DEFAULT_U_NAME_KEY):
        super().__init__(self)

        node_tuples = create_nodes_tuples(trace, activity_key, timestamp_key, u_timestamp_min_key, u_timestamp_max_key, u_missing_key, u_activity_key)
        edges_list = []

        # Adding the nodes to the graph object
        self.add_nodes_from([node for node, _ in node_tuples])

        # Applies the sweeping algorithm to the sorted list
        for i, node_tuple1 in enumerate(node_tuples):
            node1, type1 = node_tuple1
            if type1 is True:
                for node_tuple2 in node_tuples[i + 1:]:
                    node2, type2 = node_tuple2
                    if type2 is False:
                        edges_list.append((node1, node2))
                    elif (node1, node2) in edges_list:
                        break

        # Adding the edges to the graph object
        self.add_edges_from(edges_list)
