from random import random, sample
from copy import copy
from datetime import timedelta

import numpy as np
from pm4py.objects.log.util.xes import DEFAULT_TIMESTAMP_KEY

from proved.xes_keys import DEFAULT_U_TIMESTAMP_MIN_KEY, DEFAULT_U_TIMESTAMP_MAX_KEY


def add_uncertain_timestamp_to_log(p, log=None, log_map=None, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY):
    """
    Adds possible activity labels to events in a trace with a certain probability, up to a maximum.

    :param trace: the trace
    :param p: the probability of overlapping timestamps with previous events
    :param p_right: the probability of overlapping timestamps with successive events
    :param max_overlap_left: the maximum number of events that a timestamp can overlap
    :param max_overlap_right: the maximum number of events that a timestamp can overlap
    :param timestamp_key: the xes key for the timestamp
    :param u_timestamp_min_key: the xes key for the minimum value of an uncertain timestamp
    :param u_timestamp_max_key: the xes key for the maximum value of an uncertain timestamp
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

        to_alter = max(0, round(len(log_map) * p))
        indices_to_alter = sample(frozenset(log_map), to_alter)
        for i in indices_to_alter:
            trace, j = log_map[i]
            # trace[j][u_timestamp_min_key] = copy(min(trace[j][timestamp_key], trace[max(j - 1, 0)][timestamp_key]))
            # trace[j][u_timestamp_max_key] = copy(max(trace[j][timestamp_key], trace[min(j + 1, len(trace) - 1)][timestamp_key]))
            trace[j][u_timestamp_min_key] = copy(min(trace[j][timestamp_key], trace[max(j - 1, 0)][timestamp_key])) - timedelta(milliseconds=100)
            trace[j][u_timestamp_max_key] = copy(max(trace[j][timestamp_key], trace[min(j + 1, len(trace) - 1)][timestamp_key])) + timedelta(milliseconds=100)


def add_uncertain_timestamp_to_log_montecarlo(log, p_left, p_right, max_overlap_left=0, max_overlap_right=0, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY):
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
            add_uncertain_timestamp_to_trace_montecarlo(trace, p_left, p_right, max_overlap_left, max_overlap_right, timestamp_key, u_timestamp_min_key, u_timestamp_max_key)


def add_uncertain_timestamp_to_trace_montecarlo(trace, p_left, p_right, max_overlap_left=0, max_overlap_right=0, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY):
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
