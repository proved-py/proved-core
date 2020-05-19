from random import random, sample

from proved.xes_keys import DEFAULT_U_MISSING_KEY


def add_indeterminate_events_to_log(p, log=None, log_map=None, u_missing_key=DEFAULT_U_MISSING_KEY):
    """
    Turns events in an trace into indeterminate events with a certain probability.

    :param trace: the trace
    :param p: the probability of indeterminate events
    :param u_missing_key: the xes key for indeterminate events
    :return:
    """

    if p > 0.0:

        if log_map is None:
            if log is None:
                raise ValueError('Parameters log and log_map cannot both be None.')
            else:
                log_map = {}
                i = 0
                for trace in log:
                    for j in range(len(trace)):
                        log_map[i] = (trace, j)
                        i += 1

        to_add = max(0, round(len(log_map) * p))
        indices_to_add = sample(frozenset(log_map), to_add)
        for i in indices_to_add:
            trace, j = log_map[i]
            trace[j][u_missing_key] = 1


def add_indeterminate_events_to_log_montecarlo(log, p, u_missing_key=DEFAULT_U_MISSING_KEY):
    """
    Turns events in an event log into indeterminate events with a certain probability.

    :param log: the event log
    :param p: the probability of indeterminate events
    :param u_missing_key: the xes key for indeterminate events
    :return:
    """

    if p > 0.0:
        for trace in log:
            add_indeterminate_events_to_trace_montecarlo(trace, p, u_missing_key)


def add_indeterminate_events_to_trace_montecarlo(trace, p, u_missing_key=DEFAULT_U_MISSING_KEY):
    """
    Turns events in an trace into indeterminate events with a certain probability.

    :param trace: the trace
    :param p: the probability of indeterminate events
    :param u_missing_key: the xes key for indeterminate events
    :return:
    """

    if p > 0.0:
        for event in trace:
            if random() < p:
                event[u_missing_key] = 1
