from random import random, sample

from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY

from proved.xes_keys import DEFAULT_U_NAME_KEY


def add_uncertain_activities_to_log(log, p, label_set, max_labels=0, activity_key=DEFAULT_NAME_KEY, u_activity_key=DEFAULT_U_NAME_KEY):
    """
    Adds possible activity labels to events in an event log with a certain probability, up to a maximum.

    :param log: the event log
    :param p: the probability of indeterminate events
    :param label_set: the list of new possible activity labels
    :param max_labels: the maximum number of uncertain activity labels (unbounded if 0)
    :param activity_key: the xes key for the activity labels
    :param u_activity_key: the xes key for uncertain activity labels
    :return:
    """

    if p > 0:
        for trace in log:
            add_uncertain_activities_to_trace(trace, p, label_set, max_labels, activity_key, u_activity_key)


def add_uncertain_activities_to_trace(trace, p, label_set, max_labels=0, activity_key=DEFAULT_NAME_KEY, u_activity_key=DEFAULT_U_NAME_KEY):
    """
    Adds possible activity labels to events in a trace with a certain probability, up to a maximum.

    :param trace: the trace
    :param p: the probability of indeterminate events
    :param label_set: the list of new possible activity labels
    :param max_labels: the maximum number of uncertain activity labels (unbounded if 0)
    :param activity_key: the xes key for the activity labels
    :param u_activity_key: the xes key for uncertain activity labels
    :return:
    """

    if p > 0:
        for event in trace:
            to_add = 0
            if max_labels == 0 or max_labels > len(label_set):
                max_labels = len(label_set)
            while random() < p and to_add <= max_labels:
                to_add += 1
            if to_add > 0:
                event[u_activity_key]['children'] = event[activity_key] + sample(label_set - {event[activity_key]}, to_add)
