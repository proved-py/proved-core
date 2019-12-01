from datetime import datetime

from networkx import DiGraph
from networkx.algorithms.dag import transitive_reduction
from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys


# TODO: absolutely needs a comparison function
class BehaviorGraph(DiGraph):

    def __init__(self, trace, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY,
                 u_timestamp_left=xes_keys.DEFAULT_U_TIMESTAMP_LEFT_KEY,
                 u_timestamp_right=xes_keys.DEFAULT_U_TIMESTAMP_RIGHT_KEY,
                 u_missing=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        DiGraph.__init__(self)

        timestamps_list = []
        nodes_list = []
        edges_list = []
        for i, event in enumerate(trace):
            if u_activity_key not in event:
                if u_missing not in event:
                    new_node = frozenset((i, tuple([event[activity_key]])))
                else:
                    new_node = frozenset((i, tuple([event[activity_key], None])))
            else:
                if u_missing not in event:
                    new_node = frozenset((i, tuple(event[u_activity_key]['children'])))
                else:
                    new_node = frozenset((i, tuple(event[u_activity_key]['children'] + [None])))

            nodes_list.append(new_node)

            # Fill in the timestamps list
            if u_timestamp_left not in event:
                timestamps_list.append((event[timestamp_key], new_node, 'CERTAIN'))
            else:
                timestamps_list.append((event[u_timestamp_left], new_node, 'LEFT'))
                timestamps_list.append((event[u_timestamp_right], new_node, 'RIGHT'))

        # Sort timestamps_list by first term of its elements
        timestamps_list.sort()

        # Adding events 'Start' and 'End' in the list
        start = frozenset(['start'])
        nodes_list.append(start)
        self.__root = start
        end = frozenset(['end'])
        nodes_list.append(end)

        # Adding the nodes to the graph object
        self.add_nodes_from(nodes_list)

        timestamps_list.insert(0, (datetime.min, start, 'CERTAIN'))
        timestamps_list.append((datetime.max, end, 'CERTAIN'))

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

    def __get_root(self):
        return self.__root

    root = property(__get_root)


def ordered(event1, event2, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY,
            u_timestamp_left=xes_keys.DEFAULT_U_TIMESTAMP_LEFT_KEY,
            u_timestamp_right=xes_keys.DEFAULT_U_TIMESTAMP_RIGHT_KEY):
    if u_timestamp_right in event1:
        if u_timestamp_left in event2:
            return event1[u_timestamp_right] < event2[u_timestamp_left]
        else:
            return event1[u_timestamp_right] < event2[timestamp_key]
    else:
        if u_timestamp_left in event2:
            return event1[timestamp_key] < event2[u_timestamp_left]
        else:
            return event1[timestamp_key] < event2[timestamp_key]

import matplotlib.pyplot as plt
from networkx.drawing.nx_pylab import draw

class TRBehaviorGraph(DiGraph):

    def __init__(self, trace, activity_key=xes.DEFAULT_NAME_KEY, u_missing=xes_keys.DEFAULT_U_MISSING_KEY,
                 u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        DiGraph.__init__(self)

        bg = DiGraph()

        start = frozenset(['start'])
        bg.add_node(start)
        bg.__root = start
        end = frozenset(['end'])
        bg.add_node(end)

        nodes_list = []
        edges_list = []
        event_node_map = {}

        for i, event in enumerate(trace):
            if u_activity_key not in event:
                if u_missing not in event:
                    new_node = frozenset((i, tuple([event[activity_key]])))
                else:
                    new_node = frozenset((i, tuple([event[activity_key], None])))
            else:
                if u_missing not in event:
                    new_node = frozenset((i, tuple(event[u_activity_key]['children'])))
                else:
                    new_node = frozenset((i, tuple(event[u_activity_key]['children'] + [None])))

            nodes_list.append(new_node)

            edges_list.append((start, new_node))
            edges_list.append((new_node, end))
            event_node_map[i] = new_node

        for i, event1 in enumerate(trace):
            for j, event2 in enumerate(trace):
                if ordered(event1, event2):
                    edges_list.append((event_node_map[i], event_node_map[j]))

        bg.add_nodes_from(nodes_list)
        bg.add_edges_from(edges_list)

        from networkx.algorithms.dag import is_directed_acyclic_graph
        if is_directed_acyclic_graph(bg):
            # draw(bg)
            # plt.savefig('test')
            # plt.close()

            bg = transitive_reduction(bg)
        else:
            print([event['concept:name'] for event in trace])

        self.add_nodes_from(bg.nodes)
        self.__root = start
        self.add_edges_from(bg.edges)

    def __get_root(self):
        return self.__root

    root = property(__get_root)
