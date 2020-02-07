from pm4py.objects.petri.utils import acyclic_net_variants
from pm4py.algo.conformance.alignments.versions.state_equation_a_star import apply
from pm4py.algo.conformance.alignments.versions.state_equation_a_star import apply_trace_net

from proved.artifacts.behavior_graph import tr_behavior_graph
from proved.artifacts.behavior_net import behavior_net


def alignment_bounds_su_log(u_log, petri_net, initial_marking, final_marking, parameters=None):
    return [alignment_bounds_su_trace(u_trace, petri_net, initial_marking, final_marking, parameters) for u_trace in u_log]


def alignment_bounds_su_trace(u_trace, petri_net, initial_marking, final_marking, parameters=None):
    trace_net = behavior_net.BehaviorNet(tr_behavior_graph.TRBehaviorGraph(u_trace))
    return (alignment_lower_bound_su_trace(trace_net, trace_net.initial_marking, trace_net.final_marking, petri_net, initial_marking, final_marking, parameters),
            alignment_upper_bound_su_trace_bruteforce(trace_net, trace_net.initial_marking, trace_net.final_marking, petri_net, initial_marking, final_marking, parameters))


def alignment_upper_bound_su_trace_bruteforce(trace_net, tn_i, tn_f, petri_net, initial_marking, final_marking, parameters=None):
    realization_set = acyclic_net_variants(trace_net, tn_i, tn_f)
    worst_alignment = None

    for trace in realization_set:
        alignment = apply(trace, petri_net, initial_marking, final_marking, parameters)
        if alignment['cost'] > worst_alignment['cost']:
            worst_alignment = alignment

    return worst_alignment


def alignment_lower_bound_su_trace(trace_net, tn_i, tn_f, petri_net, initial_marking, final_marking, parameters=None):
    return apply_trace_net(petri_net, initial_marking, final_marking, trace_net, tn_i, tn_f, parameters)
