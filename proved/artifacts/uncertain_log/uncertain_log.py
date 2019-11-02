from pm4py.objects.log.log import EventLog

from proved.artifacts.behavior_graph import behavior_graph


class UncertainLog(EventLog):

    def __init__(self):
        EventLog.__init__(self)
        self.__behavior_graphs = dict()

    def __get_behavior_graphs(self):
        return self.__behavior_graphs

    # TODO: method that given an uncertain log creates the behavior graphs and a mapping between uncertain traces and behavior graphs
    def create_behavior_graphs(self):
        pass

    behavior_graphs = property(__get_behavior_graphs)
