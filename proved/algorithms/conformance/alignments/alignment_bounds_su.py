from pm4py.algo.conformance.alignments.petri_net.variants.state_equation_a_star import apply
from pm4py.algo.conformance.alignments.petri_net.variants.state_equation_a_star import apply_trace_net

from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net as behavior_net_builder
from proved.artifacts.behavior_net.utils import acyclic_net_variants


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
    align_lower_bound = alignment_lower_bound_su_trace(behavior_net, behavior_net.initial_marking, behavior_net.final_marking, petri_net, initial_marking, final_marking, parameters)
    align_upper_bound_real_size = alignment_upper_bound_su_trace_bruteforce(behavior_net, behavior_net.initial_marking, behavior_net.final_marking, petri_net, initial_marking, final_marking, parameters)

    return align_lower_bound, align_upper_bound_real_size[0], align_upper_bound_real_size[1]


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
    r_s = acyclic_net_variants(behavior_net, bn_i, bn_f)

    # Computes the upper bound for conformance via bruteforce on the realization set
    alignments = [apply(trace, petri_net, initial_marking, final_marking, parameters) for trace in r_s]

    return max(alignments, key=lambda x: x['cost']), len(r_s)


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
    r_s = acyclic_net_variants(behavior_net, bn_i, bn_f)

    # Computes the lower bound for conformance via bruteforce on the realization set
    alignments = [apply(trace, petri_net, initial_marking, final_marking, parameters) for trace in r_s]

    return min(alignments, key=lambda x: x['cost'])
