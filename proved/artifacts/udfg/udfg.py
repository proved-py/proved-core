from collections import defaultdict

from networkx import DiGraph

from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys
from proved.artifacts.behavior_net import behavior_net as behavior_net_builder
from proved.artifacts.behavior_net.utils import generate_all_sequences


def compute_min_max_edges_bruteforce_trivial(behavior_graphs_multiset, min_dfr_map_log, max_dfr_map_log, activity_key=xes.DEFAULT_NAME_KEY):
    """
    Computes the minimum and maximum occurrence of all directly-follows relationships
    """

    for behavior_graph, cardinality in behavior_graphs_multiset:
        behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(behavior_graph))
        realization_set = generate_all_sequences(behavior_net, behavior_net.initial_marking, behavior_net.final_marking)
        min_dfr_map_trace = defaultdict()
        max_dfr_map_trace = defaultdict()
        for realization in realization_set:
            dfr_map_realization = defaultdict(int)
            for a1, a2 in [tuple(realization[i:i+1]) for i in range(0, len(realization)-1)]:
                dfr_map_realization[(a1, a2)] += 1
            for (a1, a2), count in dfr_map_realization.items():
                if (a1, a2) not in min_dfr_map_trace or min_dfr_map_trace[(a1, a2)] > count:
                    min_dfr_map_trace[(a1, a2)] = count
                if (a1, a2) not in max_dfr_map_trace or max_dfr_map_trace[(a1, a2)] < count:
                    max_dfr_map_trace[(a1, a2)] = count
        for (a1, a2), count in min_dfr_map_trace.items():
            min_dfr_map_log[(a1, a2)] += count * cardinality
        for (a1, a2), count in max_dfr_map_trace.items():
            max_dfr_map_log[(a1, a2)] += count * cardinality


class UDFG(DiGraph):
    """
    Class representing an Uncertain Directly-Follows Graph, a graph showing the relationships between activities in an uncertain event log.
    For more information refer to:
        Pegoraro, Marco, and Wil MP van der Aalst. "Mining uncertain event data in process mining." 2019 International Conference on Process Mining (ICPM). IEEE, 2019.
    """

    def __init__(self, log, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=xes_keys.DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=xes_keys.DEFAULT_U_TIMESTAMP_MAX_KEY, u_missing_key=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        super().__init__(self)

        log_activity_labels = log.get_activity_labels()

        # UDFG in matrix form: dictionary of dictionaries string to list. activity -> (activity -> [min, max])
        # TODO: there are solutions more elegant than dict comprehension, using defaultdict and/or dict.fromkeys()
        # min_max_edges_map = {activity_label_prior: {activity_label_posterior: list([0, 0]) for activity_label_posterior in log_activity_labels} for activity_label_prior in log_activity_labels}
        min_dfr_map = defaultdict(int)
        max_dfr_map = defaultdict(int)

        compute_min_max_edges_bruteforce_trivial(log.get_behavior_graphs_multiset(), min_edges_map, max_edges_map)

        # node_tuples = create_nodes_tuples(trace, activity_key, timestamp_key, u_timestamp_min_key, u_timestamp_max_key, u_missing_key, u_activity_key)
        # edges_list = []
        #
        # # Adding the nodes to the graph object
        # self.add_nodes_from([node for node, _ in node_tuples])
        #
        # # Applies the sweeping algorithm to the sorted list
        # for i, node_tuple1 in enumerate(node_tuples):
        #     node1, type1 = node_tuple1
        #     if type1 is True:
        #         for node_tuple2 in node_tuples[i + 1:]:
        #             node2, type2 = node_tuple2
        #             if type2 is False:
        #                 edges_list.append((node1, node2))
        #             elif (node1, node2) in edges_list:
        #                 break
        #
        # # Adding the edges to the graph object
        # self.add_edges_from(edges_list)
