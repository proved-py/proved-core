from pm4py.objects import petri


def build_behavior_net(bg):
    behavior_net = petri.petrinet.PetriNet()
    start_place = petri.petrinet.PetriNet.Place('start_place')
    behavior_net.places.add(start_place)
    end_place = petri.petrinet.PetriNet.Place('end_place')
    behavior_net.places.add(end_place)

    # Creating transitions for each node in the graph
    node_trans = {}
    for i, node in enumerate(bg.nodes):
        transition_set = {petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + activity_label, activity_label) for _, activity_label in node}
        node_trans[id(node)] = transition_set
        for transition in transition_set:
            behavior_net.transitions.add(transition)

    for i, node_from in enumerate(bg.nodes):
        if not bg.successors(node_from):
            for transition in node_trans[id(node_from)]:
                petri.utils.add_arc_from_to(start_place, transition, behavior_net)

        for node_to in bg.successors(node_from):
            place = petri.petrinet.PetriNet.Place(str(id(node_from)) + str(id(node_to)))
            behavior_net.places.add(place)
            for transition in node_trans[id(node_from)]:
                petri.utils.add_arc_from_to(transition, place, behavior_net)
            for transition in node_trans[id(node_to)]:
                petri.utils.add_arc_from_to(place, transition, behavior_net)

        if not bg.predecessor(node_from):
            for transition in node_trans[id(node_from)]:
                petri.utils.add_arc_from_to(transition, end_place, behavior_net)

    return behavior_net, petri.petrinet.Marking({start_place: 1}), petri.petrinet.Marking({end_place: 1})
