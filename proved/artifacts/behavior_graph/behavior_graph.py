import operator
from datetime import timedelta, datetime

from networkx import DiGraph
from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY

from proved.xes_keys import DEFAULT_U_CONTINUOUS_STRONG, DEFAULT_U_TIMESTAMP_MIN_KEY, DEFAULT_U_TIMESTAMP_MAX_KEY, DEFAULT_U_DENSITY_FUNCTION_KEY, DEFAULT_U_NAME_KEY, DEFAULT_U_TIMESTAMP_KEY, DEFAULT_U_INDETERMINACY_KEY
from proved.artifacts.behavior_graph.utils import get_quantiles


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
        if u_timestamp_key not in event:
            nodes_tuples.append((event[timestamp_key], new_node, False))
            nodes_tuples.append((event[timestamp_key] + timedelta.resolution, new_node, True))
        elif event[u_timestamp_key]['value'] == u_continuous_strong:
            nodes_tuples.append((event[u_timestamp_key]['children'][u_timestamp_min_key], new_node, False))
            # Just to be extra safe, checks whether min and max timestamps match. If so, adds a tiny timedelta
            if event[u_timestamp_key]['children'][u_timestamp_min_key] != event[u_timestamp_key]['children'][u_timestamp_max_key]:
                nodes_tuples.append((event[u_timestamp_key]['children'][u_timestamp_max_key], new_node, True))
            else:
                nodes_tuples.append((event[u_timestamp_key]['children'][u_timestamp_max_key] + timedelta.resolution, new_node, True))
        else:
            minimum, maximum = get_quantiles(event[u_timestamp_key]['children'][u_function_key]['value'], args=dict(event[u_timestamp_key]['children'][u_function_key]['children']), p=.00001)
            # Let's ensure we do not exceed the range for timestamps
            minimum = max(minimum, datetime.timestamp(datetime(1, 1, 2, 0, 0)))
            maximum = min(maximum, datetime.timestamp(datetime(9999, 12, 31, 22, 58, 59, 999999)))
            minimum_dt = datetime.fromtimestamp(minimum).replace(tzinfo=event[timestamp_key].tzinfo)
            maximum_dt = datetime.fromtimestamp(maximum).replace(tzinfo=event[timestamp_key].tzinfo)
            nodes_tuples.append((minimum_dt, new_node, False))
            # Just to be extra safe, checks whether min and max timestamps match. If so, adds a tiny timedelta
            if minimum != maximum:
                nodes_tuples.append((maximum_dt, new_node, True))
            else:
                nodes_tuples.append((maximum_dt + timedelta.resolution, new_node, True))

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

    def __init__(self, trace, activity_key=DEFAULT_NAME_KEY, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_continuous_strong=DEFAULT_U_CONTINUOUS_STRONG, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY, u_function_key=DEFAULT_U_DENSITY_FUNCTION_KEY, u_activity_key=DEFAULT_U_NAME_KEY, u_timestamp_key=DEFAULT_U_TIMESTAMP_KEY, u_indeterminacy_key=DEFAULT_U_INDETERMINACY_KEY):
        super().__init__(self)

        node_tuples = create_nodes_tuples(trace, activity_key, timestamp_key, u_continuous_strong, u_timestamp_min_key, u_timestamp_max_key, u_function_key, u_activity_key, u_timestamp_key, u_indeterminacy_key)
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


if __name__ == '__main__':
    import pm4py
    log = pm4py.read_xes('new_format_weak_fixed_v3.xml')
    #bg1 = BehaviorGraph(log[0])
    #print(bg1.nodes)
    #print(bg1.edges)
    #from proved.visualizations.graphviz.behavior_graph import behavior_graph_graphviz
    #behavior_graph_graphviz(bg1).view()
    from proved.artifacts.uncertain_log.utils import random_realization
    for i in range(0, 3):
        for event in random_realization(log[0]):
            print(event)
        print('#########################################')
