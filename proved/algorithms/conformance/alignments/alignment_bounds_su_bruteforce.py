from pm4py.objects.petri.utils import acyclic_net_variants
from pm4py.algo.conformance.alignments.versions.state_equation_a_star import apply

from proved.artifacts.behavior_graph import tr_behavior_graph
from proved.artifacts.behavior_graph import utils

def alignment_bounds_su_log_bruteforce(u_log, petri_net, initial_marking, final_marking, parameters=None):
    return [alignment_bounds_su_trace_bruteforce(u_trace, petri_net, initial_marking, final_marking, parameters) for u_trace in u_log]


def alignment_bounds_su_trace_bruteforce(u_trace, petri_net, initial_marking, final_marking, parameters=None):
    trace_net, tn_i, tn_f = utils.build_behavior_net(tr_behavior_graph.TRBehaviorGraph(u_trace))
    realization_set = acyclic_net_variants(trace_net, tn_i, tn_f)
    best_alignment = None
    worst_alignment = None

    for trace in realization_set:
        alignment = apply(trace, petri_net, initial_marking, final_marking, parameters)
        if alignment['cost'] < best_alignment['cost']:
            best_alignment = alignment
        if alignment['cost'] > worst_alignment['cost']:
            worst_alignment = alignment

    return best_alignment, worst_alignment
