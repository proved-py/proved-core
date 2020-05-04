from random import random
from copy import copy

import numpy as np
from pm4py.objects.log.util.xes import DEFAULT_TIMESTAMP_KEY

from proved.xes_keys import DEFAULT_U_TIMESTAMP_MIN_KEY, DEFAULT_U_TIMESTAMP_MAX_KEY


def add_uncertain_timestamp_to_log_relative(log, p_left, p_right, max_overlap_left=0, max_overlap_right=0, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY):
    """
    Adds possible activity labels to events in an event log with a certain probability, up to a maximum.

    :param log: the event log
    :param p_left: the probability of overlapping timestamps with previous events
    :param p_right: the probability of overlapping timestamps with successive events
    :param max_overlap_left: the maximum number of events that a timestamp can overlap
    :param max_overlap_right: the maximum number of events that a timestamp can overlap
    :param timestamp_key: the xes key for the timestamp
    :param u_timestamp_min_key: the xes key for the minimum value of an uncertain timestamp
    :param u_timestamp_max_key: the xes key for the maximum value of an uncertain timestamp
    :return:
    """

    if p_left > 0.0 or p_right > 0.0:
        for trace in log:
            add_uncertain_timestamp_to_trace_relative(trace, p_left, p_right, max_overlap_left, max_overlap_right, timestamp_key, u_timestamp_min_key, u_timestamp_max_key)


def add_uncertain_timestamp_to_trace_relative(trace, p_left, p_right, max_overlap_left=0, max_overlap_right=0, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY):
    """
    Adds possible activity labels to events in a trace with a certain probability, up to a maximum.

    :param trace: the trace
    :param p_left: the probability of overlapping timestamps with previous events
    :param p_right: the probability of overlapping timestamps with successive events
    :param max_overlap_left: the maximum number of events that a timestamp can overlap
    :param max_overlap_right: the maximum number of events that a timestamp can overlap
    :param timestamp_key: the xes key for the timestamp
    :param u_timestamp_min_key: the xes key for the minimum value of an uncertain timestamp
    :param u_timestamp_max_key: the xes key for the maximum value of an uncertain timestamp
    :return:
    """

    if p_left > 0.0 or p_right > 0.0:
        for i in range(len(trace)):
            steps_left = 0
            steps_right = 0
            while random() < p_left and steps_left < min(max_overlap_left, i):
                steps_left += 1
            while random() < p_right and steps_right < min(max_overlap_right, len(trace) - i - 1):
                steps_right += 1
            # (Partially) supports events that already have uncertainty on timestamps
            # This might cause problems on events for which 'u_timestamp_min_key' <= 'timestamp_key' <= 'u_timestamp_max_key'
            if u_timestamp_max_key in trace[i - steps_left]:
                if u_timestamp_min_key in trace[i]:
                    trace[i][u_timestamp_min_key] = copy(min(trace[i][u_timestamp_min_key], trace[i - steps_left][u_timestamp_max_key]))
                else:
                    trace[i][u_timestamp_min_key] = copy(min(trace[i][timestamp_key], trace[i - steps_left][u_timestamp_max_key]))
            else:
                if u_timestamp_min_key in trace[i]:
                    trace[i][u_timestamp_min_key] = copy(min(trace[i][u_timestamp_min_key], trace[i - steps_left][timestamp_key]))
                else:
                    trace[i][u_timestamp_min_key] = copy(min(trace[i][timestamp_key], trace[i - steps_left][timestamp_key]))
            if u_timestamp_min_key in trace[i + steps_right]:
                if u_timestamp_max_key in trace[i]:
                    trace[i][u_timestamp_max_key] = copy(max(trace[i][u_timestamp_max_key], trace[i + steps_right][u_timestamp_min_key]))
                else:
                    trace[i][u_timestamp_max_key] = copy(max(trace[i][timestamp_key], trace[i + steps_right][u_timestamp_min_key]))
            else:
                if u_timestamp_max_key in trace[i]:
                    trace[i][u_timestamp_max_key] = copy(max(trace[i][u_timestamp_max_key], trace[i + steps_right][timestamp_key]))
                else:
                    trace[i][u_timestamp_max_key] = copy(max(trace[i][timestamp_key], trace[i + steps_right][timestamp_key]))
