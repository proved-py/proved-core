from datetime import datetime

from networkx import DiGraph
from pm4py.objects import petri
from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys


class BehaviorGraph(DiGraph):

    def __init__(self, trace, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY,
                 u_timestamp_left=xes_keys.DEFAULT_U_TIMESTAMP_LEFT_KEY, u_timestamp_right=xes_keys.DEFAULT_U_TIMESTAMP_RIGHT_KEY,
                 u_missing=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
        DiGraph.__init__(self)

        timestamps_list = []
        nodes_list = []
        edges_list = []
        for i, event in enumerate(trace):
            if u_activity_key not in event:
                # new_node = transition_system.TransitionSystem.State(str(i) + ': ' + trace[i][activity_key])
                # new_node.data = (trace[i], [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + trace[i][activity_key], trace[i][activity_key])])
                new_node = (event, [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + event[activity_key], event[activity_key])])
            else:
                # new_node = transition_system.TransitionSystem.State(
                #     str(i) + ': {' + ', '.join(list(trace[i][u_activity_key]['children'].keys())) + '}')
                # new_node.data = (trace[i], [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + activity, activity) for activity in
                #                              trace[i][u_activity_key]['children']])
                new_node = (event, [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + activity, activity) for activity in
                                    event[u_activity_key]['children']])
            if u_missing in event:
                # new_node.data[1].append(petri.petrinet.PetriNet.Transition('t' + str(i) + '_silent', None))
                new_node[1].append(petri.petrinet.PetriNet.Transition('t' + str(i) + '_silent', None))
                # if u_activity_key not in trace[i]:
                #     new_node.name = str(i) + ': {' + trace[i][activity_key] + ', ε}'
                # else:
                #     new_node.name = str(i) + ': {' + ', '.join(list(trace[i][u_activity_key]['children'].keys())) + ', ε}'

            # ts.states.add(new_node)
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
        # start = transition_system.TransitionSystem.State('start')
        # start.data = (None, [petri.petrinet.PetriNet.Transition('start', None)])
        start = (None, [petri.petrinet.PetriNet.Transition('start', None)])
        # ts.states.add(start)
        nodes_list.append(start)
        # end = transition_system.TransitionSystem.State('end')
        # end.data = (None, [petri.petrinet.PetriNet.Transition('end', None)])
        end = (None, [petri.petrinet.PetriNet.Transition('end', None)])
        # ts.states.add(end)
        nodes_list.append(end)

        # Adding the nodes to the graph object
        self.add_nodes_from(nodes_list)

        timestamps_list.insert(0, (datetime.min, start, 'CERTAIN'))
        timestamps_list.append((datetime.max, end, 'CERTAIN'))

        for i, timestamp1 in enumerate(timestamps_list):
            if timestamp1[2] != 'LEFT':
                for timestamp2 in timestamps_list[i + 1:]:
                    if timestamp2[2] == 'LEFT':
                        # utils.add_arc_from_to(repr(timestamp1[1]) + ' > ' + repr(timestamp2[1]), timestamp1[1], timestamp2[1], ts)
                        edges_list.append((timestamp1[1], timestamp2[1]))
                    if timestamp2[2] == 'CERTAIN':
                        # utils.add_arc_from_to(repr(timestamp1[1]) + ' > ' + repr(timestamp2[1]), timestamp1[1], timestamp2[1], ts)
                        edges_list.append((timestamp1[1], timestamp2[1]))
                        break
                    if timestamp2[2] == 'RIGHT':
                        if timestamp2[1] in timestamp1[1].outgoing:
                            break

        # Adding the edges to the graph object
        self.add_edges_from(edges_list)
