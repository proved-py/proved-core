#
# This bruteforce method is here just as comparison; do not actually use this. To be removed in a release
#

import pm4pycvxopt
from pm4py.objects.petri.utils import variants
from pm4py.algo.conformance.alignments.versions.state_equation_a_star import apply
from pm4py.objects.log.log import Event, Trace

from proved.algorithms.conformance.alignments.utils import construct_uncertain_trace_net


def alignment_bounds_su_log_bruteforce(u_log, petri_net, initial_marking, final_marking, parameters=None):
    return [alignment_bounds_su_trace_bruteforce(u_trace, petri_net, initial_marking, final_marking, parameters) for
            u_trace in u_log]


def alignment_bounds_su_trace_bruteforce(u_trace, petri_net, initial_marking, final_marking, parameters=None):
    trace_net, tn_i, tn_f = construct_uncertain_trace_net(u_trace)
    realization_set = variants(trace_net, tn_i, tn_f)
    best_alignment = None
    worst_alignment = None

    # TODO: this conversion should be done in the pm4py.objects.petri.utils.variants function
    for list_activities in realization_set:
        # (log_name, noise_activity, "trace ", indexp1, "aligning ", i, "out of ", len(realization_set), " list_activities")

        trace = Trace()
        for act in list_activities:
            if act is not "start" and act is not "end":
                if act[0] is not "n":
                    e = Event()
                    e["concept:name"] = act
                    trace.append(e)
                else:
                    try:
                        int(act[1:])
                    except:
                        e = Event()
                        e["concept:name"] = act
                        trace.append(e)

        alignment = apply(trace, petri_net, initial_marking, final_marking, parameters)
        if alignment['cost'] < best_alignment['cost']:
            best_alignment = alignment
        if alignment['cost'] > worst_alignment['cost']:
            worst_alignment = alignment

    return best_alignment, worst_alignment
