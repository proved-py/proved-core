from pm4py.objects import petri


def build_behavior_net(behavior_graph):
    behavior_net = petri.petrinet.PetriNet()

    source_place = petri.petrinet.PetriNet.Place('source')
    behavior_net.places.add(source_place)
    source_trans = petri.petrinet.PetriNet.Transition('t_source', None)
    behavior_net.transitions.add(source_trans)
    petri.utils.add_arc_from_to(source_place, source_trans, behavior_net)

    sink_place = petri.petrinet.PetriNet.Place('sink')
    behavior_net.places.add(sink_place)
    sink_trans = petri.petrinet.PetriNet.Transition('t_sink', None)
    behavior_net.transitions.add(sink_trans)
    petri.utils.add_arc_from_to(sink_trans, sink_place, behavior_net)

    # Creating transitions for each node in the graph
    node_trans = {}
    for i, node in enumerate(behavior_graph.nodes):
        transition_set = {petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + str(activity_label), activity_label) for activity_label in node[1]}
        node_trans[id(node)] = transition_set
        for transition in transition_set:
            behavior_net.transitions.add(transition)

    for i, node_from in enumerate(behavior_graph.nodes):
        if not next(behavior_graph.predecessors(node_from), None):
            for transition in node_trans[id(node_from)]:
                place_from_source = petri.petrinet.PetriNet.Place('source_to_' + str(transition.label) + '_of_' + str(id(node_from)))
                behavior_net.places.add(place_from_source)
                petri.utils.add_arc_from_to(source_trans, place_from_source, behavior_net)
                petri.utils.add_arc_from_to(place_from_source, transition, behavior_net)

        for node_to in behavior_graph.successors(node_from):
            place = petri.petrinet.PetriNet.Place(str(id(node_from)) + str(id(node_to)))
            behavior_net.places.add(place)
            for transition in node_trans[id(node_from)]:
                petri.utils.add_arc_from_to(transition, place, behavior_net)
            for transition in node_trans[id(node_to)]:
                petri.utils.add_arc_from_to(place, transition, behavior_net)

        if not next(behavior_graph.successors(node_from), None):
            for transition in node_trans[id(node_from)]:
                place_to_sink = petri.petrinet.PetriNet.Place(str(transition.label) + '_of_' + str(id(node_from)) + '_to_sink')
                behavior_net.places.add(place_to_sink)
                petri.utils.add_arc_from_to(transition, place_to_sink, behavior_net)
                petri.utils.add_arc_from_to(place_to_sink, sink_trans, behavior_net)

    return behavior_net, petri.petrinet.Marking({source_place: 1}), petri.petrinet.Marking({sink_place: 1})
