from statistics import mean

from proved.algorithms.conformance.alignments.alignment_bounds_su import alignment_bounds_su_trace, alignment_bounds_su_log


def alignment_based_trace_fitness(u_trace, petri_net, initial_marking, final_marking, parameters=None):
    alignment_lower_bound, alignment_upper_bound = alignment_bounds_su_trace(u_trace, petri_net, initial_marking, final_marking, parameters)
    return alignment_lower_bound['fitness'], alignment_upper_bound['fitness']


# TODO: see proved.algorithms.conformance.alignments.alignment_bounds_su.alignment_bounds_su_log, needs to be smarter and receive a dictionary
def alignment_based_log_fitness(u_log, petri_net, initial_marking, final_marking, parameters=None):
    log_alignments = list(zip(*alignment_bounds_su_log(u_log, petri_net, initial_marking, final_marking, parameters)))
    return mean(log_alignments[0]), mean(log_alignments[1])
