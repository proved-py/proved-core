from pm4py.objects.log.log import EventLog

from proved.artifacts.behavior_graph import behavior_graph


class UncertainLog(EventLog):

    def __init__(self, log=None):
        self.__variants = dict()
        self.__behavior_graphs_map = dict()
        if log is not None:
            EventLog.__init__(self, log)
            self.create_behavior_graphs()
        else:
            EventLog.__init__(self)

    def __get_variants(self):
        return self.__variants

    def __get_behavior_graphs_map(self):
        return self.__behavior_graphs_map

    def create_behavior_graphs(self):
        for trace in self:
            nodes_tuple = behavior_graph.create_nodes_tuples(trace)
            if nodes_tuple not in self.behavior_graphs_map:
                self.behavior_graphs_map[nodes_tuple] = (behavior_graph.BehaviorGraph(trace), [])
            self.behavior_graphs_map[nodes_tuple][1].append(trace)
        if self.behavior_graphs_map is not {}:
            variant_list = [(len(traces_list), nodes_list) for nodes_list, (_, traces_list) in self.behavior_graphs_map.items()]
            variant_list.sort(reverse=True)
            self.__variants = {i: (variant_cardinality, nodes_tuple) for i, (variant_cardinality, nodes_tuple) in enumerate(variant_list)}

    def get_behavior_graph(self, trace):
        # return self.behavior_graphs_map[behavior_graph.create_nodes_tuples(trace)]
        return self.behavior_graphs_map[behavior_graph.create_nodes_tuples(trace)][0]

    def get_behavior_graphs_multiset(self):
        return [(graph, len(traces_list)) for graph, traces_list in self.behavior_graphs_map.values()]

    def get_cardinality(self, trace):
        return len(self.behavior_graphs_map[behavior_graph.create_nodes_tuples(trace)][1])

    def get_activity_labels(self):  # TODO: test this
        log_activity_labels = set()
        for (_, nodes_tuple) in self.__variants.values():
            for ((_, activity_labels), _) in nodes_tuple:
                log_activity_labels.update(activity_labels)
        return log_activity_labels

    variants = property(__get_variants)
    behavior_graphs_map = property(__get_behavior_graphs_map)
