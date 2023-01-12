from random import random, sample

from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY

from proved.xes_keys import DEFAULT_U_DISCRETE_STRONG, DEFAULT_U_NAME_KEY


def add_uncertain_activities_to_log(p, log=None, log_map=None, max_labels_to_add=1, label_set=None, activity_key=DEFAULT_NAME_KEY, u_discrete_strong=DEFAULT_U_DISCRETE_STRONG, u_activity_key=DEFAULT_U_NAME_KEY):
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

    if p > 0.0:

        build_label_set = False
        if label_set is None:
            build_label_set = True

        if log_map is None:
            if log is None:
                raise ValueError('Parameters log and log_map cannot both be None.')
            else:
                log_map = {}
                if build_label_set:
                    label_set = set()
                i = 0
                for trace in log:
                    for j in range(len(trace)):
                        log_map[i] = (trace, j)
                        if build_label_set:
                            label_set.add(trace[j][activity_key])
                        i += 1

        to_alter = max(0, round(len(log_map) * p))
        indices_to_alter = sample(frozenset(log_map), to_alter)
        labels_to_add = min(max_labels_to_add, len(label_set) - 1)
        for i in indices_to_alter:
            trace, j = log_map[i]
            trace[j][u_activity_key] = dict()
            trace[j][u_activity_key]['value'] = u_discrete_strong
            trace[j][u_activity_key]['children'] = {activity_label: None for activity_label in [trace[j][activity_key]] + sample(list(label_set - {trace[j][activity_key]}), labels_to_add)}


def add_uncertain_activities_to_log_montecarlo(log, p, max_labels=0, label_set=None, activity_key=DEFAULT_NAME_KEY, u_discrete_strong=DEFAULT_U_DISCRETE_STRONG, u_activity_key=DEFAULT_U_NAME_KEY):
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

    if p > 0.0:
        if label_set is None:
            label_set = set()
            for trace in log:
                for event in trace:
                    label_set.add(event[activity_key])
        for trace in log:
            add_uncertain_activities_to_trace_montecarlo(trace, p, label_set, max_labels, activity_key, u_discrete_strong, u_activity_key)


def add_uncertain_activities_to_trace_montecarlo(trace, p, max_labels=0, label_set=None, activity_key=DEFAULT_NAME_KEY, u_discrete_strong=DEFAULT_U_DISCRETE_STRONG, u_activity_key=DEFAULT_U_NAME_KEY):
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

    if p > 0.0:
        if label_set is None:
            label_set = set()
            for event in trace:
                label_set.add(event[activity_key])
        for event in trace:
            to_add = 0
            if max_labels == 0 or max_labels > len(label_set):
                if u_activity_key not in event:
                    max_labels = len(label_set) - 1
                else:
                    max_labels = len(label_set) - len(event[u_activity_key]['children'])
            while random() < p and to_add < max_labels:
                to_add += 1
            if to_add > 0:
                if u_activity_key not in event:
                    event[u_activity_key] = dict()
                    event[u_activity_key]['value'] = u_discrete_strong
                    event[u_activity_key]['children'] = {activity_label: 0 for activity_label in [event[activity_key]] + sample(label_set - {event[activity_key]}, to_add)}
                else:
                    event[u_activity_key]['children'].update({activity_label: 0 for activity_label in [event[activity_key]] + sample(label_set - {event[activity_key]}, to_add)})
