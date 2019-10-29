from proved.algorithms.conformance.alignments.alignment_bounds_su import alignment_bounds_su_trace, alignment_bounds_su_log


def alignment_based_trace_fitness(u_trace, petri_net, initial_marking, final_marking, parameters=None):
    alignment_lower_bound, alignment_upper_bound = alignment_bounds_su_trace(u_trace, petri_net, initial_marking, final_marking, parameters=None)
    return (alignment_lower_bound['fitness'], alignment_upper_bound['fitness'])
