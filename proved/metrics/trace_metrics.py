from proved.artifacts.uncertain_log.utils import realization_set


def trace_variability(trace):
    return 1/len(realization_set(trace))
