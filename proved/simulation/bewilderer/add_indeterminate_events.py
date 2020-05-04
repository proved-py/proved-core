from random import random

from proved.xes_keys import DEFAULT_U_MISSING_KEY


def add_indeterminate_events_to_log(log, p, u_missing_key=DEFAULT_U_MISSING_KEY):
    """
    Turns events in an event log into indeterminate events with a certain probability.

    :param log: the event log
    :param p: the probability of indeterminate events
    :param u_missing_key: the xes key for indeterminate events
    :return:
    """

    if p > 0.0:
        for trace in log:
            add_indeterminate_events_to_trace(trace, p, u_missing_key)


def add_indeterminate_events_to_trace(trace, p, u_missing_key=DEFAULT_U_MISSING_KEY):
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
