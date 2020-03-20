from random import random

import proved.xes_keys as xes_keys


def add_indeterminate_events_to_log(log, p, u_missing=xes_keys.DEFAULT_U_MISSING_KEY):
    """
    Turns events in an event log into indeterminate events with a certain probability.

    :param log: the event log
    :param p: the probability of indeterminate events
    :param u_missing: the xes key for indeterminate events
    :return:
    """
    for trace in log:
        add_indeterminate_events_to_trace(trace, p, u_missing)


def add_indeterminate_events_to_trace(trace, p, u_missing=xes_keys.DEFAULT_U_MISSING_KEY):
    """
    Turns events in an trace into indeterminate events with a certain probability.

    :param trace: the trace
    :param p: the probability of indeterminate events
    :param u_missing: the xes key for indeterminate events
    :return:
    """
    for event in trace:
        if random() < p:
            event[u_missing] = 1
