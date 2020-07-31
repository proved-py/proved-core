# from pm4py.objects.petri.utils import acyclic_net_variants
from pm4py.algo.conformance.alignments.versions.state_equation_a_star import apply
from pm4py.algo.conformance.alignments.versions.state_equation_a_star import apply_trace_net

from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net as behavior_net_builder


from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY
from pm4py.objects.log.log import Trace, Event
from pm4py.objects import petri
def acyclic_net_variants_new(net, initial_marking, final_marking, activity_key=DEFAULT_NAME_KEY):
    """
    Given an acyclic accepting Petri net, initial and final marking extracts a set of variants (in form of traces)
    replayable on the net.
    Warning: this function is based on a marking exploration. If the accepting Petri net contains loops, the method
    will not work properly as it stops the search if a specific marking has already been encountered.

    Parameters
    ----------
    :param net: An acyclic workflow net
    :param initial_marking: The initial marking of the net.
    :param final_marking: The final marking of the net.
    :param shallow: If true, the event attributes might reference the same objects (the output might suffer side effects if not used for read-only operations, but the method is faster)

    Returns
    -------
    :return: variants: :class:`list` Set of variants - in the form of Trace objects - obtainable executing the net

    """
    active = {(initial_marking, ())}
    visited = set()
    variants = set()
    hash_final_marking = hash(final_marking)
    while active:
        curr_marking, curr_partial_trace = active.pop()
        hash_curr_pair = hash((curr_marking, curr_partial_trace))
        enabled_transitions = petri.semantics.enabled_transitions(net, curr_marking)
        for transition in enabled_transitions:
            if transition.label is not None:
                next_partial_trace = curr_partial_trace + (repr(transition),)
            else:
                next_partial_trace = curr_partial_trace
            next_marking = petri.semantics.execute(transition, net, curr_marking)
            hash_next_pair = hash((next_marking, next_partial_trace))

            if hash(next_marking) == hash_final_marking:
                variants.add(next_partial_trace)
            else:
                # If the next marking hash is not in visited, if the next marking+partial trace is different from the current one+partial trace
                if hash_next_pair not in visited and hash_curr_pair != hash_next_pair:
                    active.add((next_marking, next_partial_trace))
        visited.add(hash_curr_pair)
    trace_variants = []
    for variant in variants:
        trace = Trace()
        for activity_label in variant:
            trace.append(Event({activity_key: activity_label}))
        trace_variants.append(trace)
    return trace_variants


def alignment_bounds_su_log(log, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower and upper bounds for conformance of a strongly uncertain log against a reference Petri net.

    :param log: the strongly uncertain event log
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: a list of 2-tuples containing the alignment results for the upper and lower bounds for conformance of the traces in the log
    """

    return [alignment_bounds_su_trace(trace, petri_net, initial_marking, final_marking, parameters) for trace in log]


def alignment_bounds_su_trace(trace, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower and upper bounds for conformance of a strongly uncertain trace against a reference Petri net by aligning all possible realizations.

    :param trace: the strongly uncertain trace
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: a 2-tuple containing the alignment results for the upper and lower bounds for conformance of the trace
    """

    # Obtains the behavior net of the trace
    behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))

    return alignment_lower_bound_su_trace(behavior_net, behavior_net.initial_marking, behavior_net.final_marking, petri_net, initial_marking, final_marking, parameters), alignment_upper_bound_su_trace_bruteforce(behavior_net, behavior_net.initial_marking, behavior_net.final_marking, petri_net, initial_marking, final_marking, parameters)


def alignment_upper_bound_su_trace_bruteforce(behavior_net, bn_i, bn_f, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the upper bound for conformance of a strongly uncertain trace against a reference Petri net by aligning all possible realizations.

    :param behavior_net: the behavior net of a strongly uncertain trace
    :param bn_i: the initial marking of the behavior net
    :param bn_f: the final marking of the behavior net
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: the alignment results for the upper bound for conformance of the trace
    """

    # Obtains all the realizations of the trace by executing all possible variants from the behavior net
    realization_set = acyclic_net_variants_new(behavior_net, bn_i, bn_f)

    # Computes the upper bound for conformance via bruteforce on the realization set
    alignments = [apply(trace, petri_net, initial_marking, final_marking, parameters) for trace in realization_set]

    return max(alignments, key=lambda x: x['cost'])


def alignment_lower_bound_su_trace(behavior_net, bn_i, bn_f, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower bound for conformance of a strongly uncertain trace against a reference Petri net by aligning using the product between the reference Petri net and the behavior net of the trace.

    :param behavior_net: the behavior net of a strongly uncertain trace
    :param bn_i: the initial marking of the behavior net
    :param bn_f: the final marking of the behavior net
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: the alignment results for the lower bound for conformance of the trace
    """

    return apply_trace_net(petri_net, initial_marking, final_marking, behavior_net, bn_i, bn_f, parameters)


def alignment_lower_bound_su_trace_bruteforce(behavior_net, bn_i, bn_f, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower bound for conformance of a strongly uncertain trace against a reference Petri net by aligning all possible realizations.

    :param behavior_net: the behavior net of a strongly uncertain trace
    :param bn_i: the initial marking of the behavior net
    :param bn_f: the final marking of the behavior net
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: the alignment results for the upper bound for conformance of the trace
    """

    # Obtains all the realizations of the trace by executing all possible variants from the behavior net
    realization_set = acyclic_net_variants_new(behavior_net, bn_i, bn_f)

    # Computes the lower bound for conformance via bruteforce on the realization set
    alignments = [apply(trace, petri_net, initial_marking, final_marking, parameters) for trace in realization_set]

    return min(alignments, key=lambda x: x['cost'])










def exec_alignment_lower_bound_su_log_bruteforce(log, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower and upper bounds for conformance of a strongly uncertain log against a reference Petri net.

    :param log: the strongly uncertain event log
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: a list of 2-tuples containing the alignment results for the upper and lower bounds for conformance of the traces in the log
    """

    realization_set_sizes_list = []
    for trace in log:
        behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))

        # Obtains all the realizations of the trace by executing all possible variants from the behavior net
        # print('IN', flush=True)
        # from pm4py.visualization.petrinet import factory as pt_vis
        # gviz = pt_vis.apply(behavior_net, behavior_net.initial_marking, behavior_net.final_marking)
        # pt_vis.view(gviz)
        realization_set = acyclic_net_variants_new(behavior_net, behavior_net.initial_marking, behavior_net.final_marking)
        # print('OUT', flush=True)
        realization_set_sizes_list.append(len(realization_set))

        # Computes the lower bound for conformance via bruteforce on the realization set
        for realization in realization_set:
            apply(realization, petri_net, initial_marking, final_marking, parameters)

    return realization_set_sizes_list


def exec_alignment_lower_bound_su_log(log, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower and upper bounds for conformance of a strongly uncertain log against a reference Petri net.

    :param log: the strongly uncertain event log
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: a list of 2-tuples containing the alignment results for the upper and lower bounds for conformance of the traces in the log
    """

    for trace in log:
        behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))

        apply_trace_net(petri_net, initial_marking, final_marking, behavior_net, behavior_net.initial_marking, behavior_net.final_marking, parameters)















def cost_bounds_su_log(log, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower and upper bounds for conformance of a strongly uncertain log against a reference Petri net.

    :param log: the strongly uncertain event log
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: a list of 2-tuples containing the alignment results for the upper and lower bounds for conformance of the traces in the log
    """

    return [cost_bounds_su_trace(u_trace, petri_net, initial_marking, final_marking, parameters) for u_trace in log]


def cost_bounds_su_trace(trace, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower and upper bounds for conformance of a strongly uncertain trace against a reference Petri net by aligning all possible realizations.

    :param trace: the strongly uncertain trace
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: a 2-tuple containing the alignment results for the upper and lower bounds for conformance of the trace
    """

    # Obtains the behavior net of the trace
    behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))

    return cost_lower_bound_su_trace(behavior_net, behavior_net.initial_marking, behavior_net.final_marking, petri_net, initial_marking, final_marking, parameters), cost_upper_bound_su_trace_bruteforce(behavior_net, behavior_net.initial_marking, behavior_net.final_marking, petri_net, initial_marking, final_marking, parameters)


def cost_upper_bound_su_trace_bruteforce(behavior_net, bn_i, bn_f, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the upper bound for conformance of a strongly uncertain trace against a reference Petri net by aligning all possible realizations.

    :param behavior_net: the behavior net of a strongly uncertain trace
    :param bn_i: the initial marking of the behavior net
    :param bn_f: the final marking of the behavior net
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: the alignment results for the upper bound for conformance of the trace
    """

    # Obtains all the realizations of the trace by executing all possible variants from the behavior net
    realization_set = acyclic_net_variants_new(behavior_net, bn_i, bn_f)

    # Computes the upper bound for conformance via bruteforce on the realization set
    costs = []
    for trace in realization_set:
        hash_act_tuple = hash(tuple(event['concept:name'] for event in trace))
        if hash_act_tuple in parameters['ALIGNMENTS_MEMO']:
            costs.append(parameters['ALIGNMENTS_MEMO'][hash_act_tuple])
        else:
            cost = apply(trace, petri_net, initial_marking, final_marking, parameters)['cost']
            costs.append(cost)
            parameters['ALIGNMENTS_MEMO'][hash_act_tuple] = cost

    return max(costs)


def cost_lower_bound_su_trace(behavior_net, bn_i, bn_f, petri_net, initial_marking, final_marking, parameters=None):
    """
    Returns the lower bound for conformance of a strongly uncertain trace against a reference Petri net by aligning using the product between the reference Petri net and the behavior net of the trace.

    :param behavior_net: the behavior net of a strongly uncertain trace
    :param bn_i: the initial marking of the behavior net
    :param bn_f: the final marking of the behavior net
    :param petri_net: the reference Petri net
    :param initial_marking: the initial marking of the reference Petri net
    :param final_marking: the final marking of the reference Petri net
    :param parameters: the optional parameters for alignments
    :return: the alignment results for the lower bound for conformance of the trace
    """

    return alignment_lower_bound_su_trace(behavior_net, bn_i, bn_f, petri_net, initial_marking, final_marking, parameters)['cost']

