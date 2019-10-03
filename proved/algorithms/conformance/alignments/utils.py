from pm4py.objects import petri
from pm4py.objects.log.util import xes
from pm4py.objects.transition_system import transition_system, utils

import proved.xes_keys as xes_keys


# TODO: not needed when the quick construction of the behavior graph is ready
def ordered(event1, event2, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY, u_timestamp_left=xes_keys.DEFAULT_U_TIMESTAMP_LEFT_KEY,
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


def construct_behavior_graph(trace, activity_key=xes.DEFAULT_NAME_KEY, u_missing=xes_keys.DEFAULT_U_MISSING_KEY,
                             u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
    ts = transition_system.TransitionSystem()
    start = transition_system.TransitionSystem.State('start')
    start.data = (None, [petri.petrinet.PetriNet.Transition('start', None)])
    ts.states.add(start)
    end = transition_system.TransitionSystem.State('end')
    end.data = (None, [petri.petrinet.PetriNet.Transition('end', None)])
    ts.states.add(end)
    for i in range(0, len(trace)):
        if u_activity_key not in trace[i]:
            new_state = transition_system.TransitionSystem.State(trace[i][activity_key] + str(i))
            new_state.data = (trace[i], [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + trace[i][activity_key], trace[i][activity_key])])
        else:
            new_state = transition_system.TransitionSystem.State('_'.join(list(trace[i][u_activity_key]['children'].keys())) + str(i))
            new_state.data = (trace[i], [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + activity, activity) for activity in
                                         trace[i][u_activity_key]['children']])
        if u_missing in trace[i]:
            new_state.data[1].append(petri.petrinet.PetriNet.Transition('t' + str(i) + '_silent', None))
            new_state.name = new_state.name + '_ε'

        utils.add_arc_from_to('start_' + repr(new_state), start, new_state, ts)
        utils.add_arc_from_to(repr(new_state) + '_end', new_state, end, ts)
        for state in ts.states:
            if state.name is not 'start' and state.name is not 'end' and ordered(state.data[0], trace[i]):
                utils.add_arc_from_to(repr(state) + repr(new_state), state, new_state, ts)
        ts.states.add(new_state)

    utils.transitive_reduction(ts)
    return ts


# TODO: unfinished
def construct_behavior_graph_quick(trace, activity_key=xes.DEFAULT_NAME_KEY, timestamp_key=xes.DEFAULT_TIMESTAMP_KEY,
                                   u_timestamp_left=xes_keys.DEFAULT_U_TIMESTAMP_LEFT_KEY, u_timestamp_right=xes_keys.DEFAULT_U_TIMESTAMP_RIGHT_KEY,
                                   u_missing=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
    ts = transition_system.TransitionSystem()
    # start = transition_system.TransitionSystem.State('start')
    # start.data = (None, [petri.petrinet.PetriNet.Transition('start', None)])
    # ts.states.add(start)
    # end = transition_system.TransitionSystem.State('end')
    # end.data = (None, [petri.petrinet.PetriNet.Transition('end', None)])
    # ts.states.add(end)

    ## TODO: add events 'Start' and 'End' in the trace, instead of directly in the graph
    t_list = []
    for i in range(0, len(trace)):
        if u_activity_key not in trace[i]:
            new_state = transition_system.TransitionSystem.State(trace[i][activity_key] + str(i))
            new_state.data = (trace[i], [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + trace[i][activity_key], trace[i][activity_key])])
        else:
            new_state = transition_system.TransitionSystem.State('_'.join(list(trace[i][u_activity_key]['children'].keys())) + str(i))
            new_state.data = (trace[i], [petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + activity, activity) for activity in
                                         trace[i][u_activity_key]['children']])
        if u_missing in trace[i]:
            new_state.data[1].append(petri.petrinet.PetriNet.Transition('t' + str(i) + '_silent', None))
            new_state.name = new_state.name + '_ε'

        ts.states.add(new_state)

        # Fill in the timestamps list
        if u_timestamp_left not in trace[i]:
            t_list.append((trace[i]['timestamp_key'], new_state, 'CERTAIN'))
        else:
            t_list.append((trace[i]['u_timestamp_left'], new_state, 'LEFT'))
            t_list.append((trace[i]['u_timestamp_right'], new_state, 'RIGHT'))


def construct_uncertain_trace_net(trace, trace_name_key=xes.DEFAULT_NAME_KEY):
    ts = construct_behavior_graph(trace)

    net = petri.petrinet.PetriNet('trace net of %s' % trace.attributes[trace_name_key] if trace_name_key in trace.attributes else ' ')
    start_place = petri.petrinet.PetriNet.Place('start_place')
    net.places.add(start_place)
    end_place = petri.petrinet.PetriNet.Place('end_place')
    net.places.add(end_place)
    for state in ts.states:
        for transition in state.data[1]:
            net.transitions.add(transition)

    for state in ts.states:
        if state.name == 'start':
            petri.utils.add_arc_from_to(start_place, state.data[1][0], net)

        for arc in state.outgoing:
            place = petri.petrinet.PetriNet.Place(str(id(state)) + str(id(arc)))
            net.places.add(place)
            for transition in state.data[1]:
                petri.utils.add_arc_from_to(transition, place, net)
            for transition in arc.to_state.data[1]:
                petri.utils.add_arc_from_to(place, transition, net)

        if state.name == 'end':
            petri.utils.add_arc_from_to(state.data[1][0], end_place, net)
    return net, petri.petrinet.Marking({start_place: 1}), petri.petrinet.Marking({end_place: 1})