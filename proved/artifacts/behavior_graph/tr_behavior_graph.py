from networkx import DiGraph
from networkx.algorithms.dag import transitive_reduction
from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys


def ordered(event1, event2, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY, u_timestamp_min=xes_keys.DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max=xes_keys.DEFAULT_U_TIMESTAMP_MAX_KEY):
    """
    Method that determines the time order of two non-overlapping events.

    :param event1: the first event
    :param event2: the second event
    :param timestamp_key: keyword to access the event timestamp
    :param u_timestamp_min: keyword to access the minimum event timestamp
    :param u_timestamp_max: keyword to access the maximum event timestamp
    :return: True if event1 happened before event2 and they are not overlapping, FALSE otherwise
    """

    if u_timestamp_max in event1:
        if u_timestamp_min in event2:
            return event1[u_timestamp_max] < event2[u_timestamp_min]
        else:
            return event1[u_timestamp_max] < event2[timestamp_key]
    else:
        if u_timestamp_min in event2:
            return event1[timestamp_key] < event2[u_timestamp_min]
        else:
            return event1[timestamp_key] < event2[timestamp_key]


class TRBehaviorGraph(DiGraph):
    """
    Class representing a behavior graph obtained through transitive reduction.
    For more information refer to:
        Pegoraro, Marco, and Wil MP van der Aalst. "Mining uncertain event data in process mining." 2019 International Conference on Process Mining (ICPM). IEEE, 2019.
    """

    def __init__(self, trace, activity_key=xes.DEFAULT_NAME_KEY, u_missing=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        DiGraph.__init__(self)

        bg = DiGraph()

        nodes_list = []
        edges_list = []
        event_node_map = {}

        # Creates nodes of the behavior graph (2-tuples composed of an integer and a set of activity labels)
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
            event_node_map[i] = new_node

        # Creates edges by connecting the nodes that are in order
        for i, event1 in enumerate(trace):
            for j, event2 in enumerate(trace):
                if ordered(event1, event2):
                    edges_list.append((event_node_map[i], event_node_map[j]))

        bg.add_nodes_from(nodes_list)
        bg.add_edges_from(edges_list)

        # Performs the transitive reduction
        bg = transitive_reduction(bg)

        self.add_nodes_from(bg.nodes)
        self.add_edges_from(bg.edges)
