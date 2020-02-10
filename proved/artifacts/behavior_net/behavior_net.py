from pm4py.objects import petri


class BehaviorNet(petri.petrinet.PetriNet):
    """
    Class that represetn a behavior net, a sound workflow Petri net that can replay all realizations of an uncertain trace.
    For more information refer to:
        Pegoraro, Marco, and Wil MP van der Aalst. "Mining uncertain event data in process mining." 2019 International Conference on Process Mining (ICPM). IEEE, 2019.
    """

    def __init__(self, behavior_graph):
        petri.petrinet.PetriNet.__init__(self)

        # Creating sink and source place, and invisible transitions connecting them to the rest of the net
        source_place = petri.petrinet.PetriNet.Place('source')
        self.places.add(source_place)
        source_trans = petri.petrinet.PetriNet.Transition('t_source', None)
        self.transitions.add(source_trans)
        petri.utils.add_arc_from_to(source_place, source_trans, self)

        sink_place = petri.petrinet.PetriNet.Place('sink')
        self.places.add(sink_place)
        sink_trans = petri.petrinet.PetriNet.Transition('t_sink', None)
        self.transitions.add(sink_trans)
        petri.utils.add_arc_from_to(sink_trans, sink_place, self)

        # Creating transitions for each node in the graph
        node_trans = {}
        for i, node in enumerate(behavior_graph.nodes):
            transition_set = {petri.petrinet.PetriNet.Transition('t' + str(i) + '_' + str(activity_label), activity_label) for activity_label in node[1]}
            node_trans[id(node)] = transition_set
            for transition in transition_set:
                self.transitions.add(transition)

        for i, node_from in enumerate(behavior_graph.nodes):
            # Each activity that can start the trace have to be connected through an AND-split to the starting invisible transition
            if not next(behavior_graph.predecessors(node_from), None):
                place_from_source = petri.petrinet.PetriNet.Place('source_to_' + str(id(node_from)))
                for transition in node_trans[id(node_from)]:
                    self.places.add(place_from_source)
                    petri.utils.add_arc_from_to(place_from_source, transition, self)
                petri.utils.add_arc_from_to(source_trans, place_from_source, self)

            # Every arc in the behavior graph is translated to a place in the behavior net, describing the precedence relationship between nodes
            # For each successor of the current node, all the transitions of the current node are connected to all the transitions in the successor through a place
            for node_to in behavior_graph.successors(node_from):
                place = petri.petrinet.PetriNet.Place(str(id(node_from)) + str(id(node_to)))
                self.places.add(place)
                for transition in node_trans[id(node_from)]:
                    petri.utils.add_arc_from_to(transition, place, self)
                for transition in node_trans[id(node_to)]:
                    petri.utils.add_arc_from_to(place, transition, self)

            # Each activity that can end the trace have to be connected through an AND-join to the ending invisible transition
            if not next(behavior_graph.successors(node_from), None):
                place_to_sink = petri.petrinet.PetriNet.Place(str(id(node_from)) + '_to_sink')
                for transition in node_trans[id(node_from)]:
                    self.places.add(place_to_sink)
                    petri.utils.add_arc_from_to(transition, place_to_sink, self)
                petri.utils.add_arc_from_to(place_to_sink, sink_trans, self)

        # Initial and final markings are just one token in the source place and one token in the sink place, respectively
        self.initial_marking = petri.petrinet.Marking({source_place: 1})
        self.final_marking = petri.petrinet.Marking({sink_place: 1})

    def __set_initial_marking(self, initial_marking):
        self.__initial_marking = initial_marking

    def __get_initial_marking(self):
        return self.__initial_marking

    def __set_final_marking(self, final_marking):
        self.__final_marking = final_marking

    def __get_final_marking(self):
        return self.__final_marking

    initial_marking = property(__get_initial_marking, __set_initial_marking)
    final_marking = property(__get_final_marking, __set_final_marking)
