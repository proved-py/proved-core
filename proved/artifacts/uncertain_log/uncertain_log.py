from pm4py.objects.log.log import EventLog

from proved.artifacts.behavior_graph import behavior_graph


class UncertainLog(EventLog):

    def __init__(self, log=None):
        self.__behavior_graphs = dict()
        if log is not None:
            EventLog.__init__(self, log)
            self.create_behavior_graphs()
        else:
            EventLog.__init__(self)

    def __get_behavior_graphs(self):
        return self.__behavior_graphs

    # TODO: method that given an uncertain log creates the behavior graphs and a mapping between uncertain traces and behavior graphs
    def create_behavior_graphs(self):
        # TODO: this still suffers from the bug of the behavior graph creation: timestamps must not coincide
        for trace in self:
            nodes_list = behavior_graph.create_nodes_tuples(trace)
            if nodes_list not in self.behavior_graphs:
                self.behavior_graphs[nodes_list] = (behavior_graph.BehaviorGraph(trace), [])
            self.behavior_graphs[nodes_list][1].append(trace)

    def create_sorted_variant_tuple(self):
        if self.behavior_graphs is not {}:
            variant_list = [(len(variant[1]), i, variant[0], variant[1]) for i, (nodes_list, variant) in enumerate(self.behavior_graphs.items())]
            variant_list.sort(reverse=True)
            return tuple(variant_list)

    behavior_graphs = property(__get_behavior_graphs)
