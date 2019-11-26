import random
import time

import numpy as np

from proved.artifacts.behavior_graph import behavior_graph


def generate_time_interval(curr_eve_timestamp, max_timeinterval_length):
    """
    Generate a time interval for uncertain event

    Parameters
    ------------
    curr_eve_timestamp
        Current timestamp (from 1970, adding 1 seconds each time) corresponding to the event
    max_timeinterval_length
        Maximum (time) length of the uncertain interval

    Returns
    ------------
    interval
        Time interval for the uncertain event
    """
    left_random = random.random() * max(0, curr_eve_timestamp - max_timeinterval_length / 2)
    right_random = random.random() * (max_timeinterval_length - left_random)

    return [int(curr_eve_timestamp - left_random), int(curr_eve_timestamp + right_random)]


def introduce_uncertainty(log, act_labels, parameters):
    if parameters is None:
        parameters = {}
    p_u_activity = parameters["p_u_activity"] if "p_u_activity" in parameters else 0
    n_u_activity = parameters["n_u_activity"] if "n_u_activity" in parameters else 0
    p_u_time = parameters["p_u_time"] if "p_u_time" in parameters else 0
    max_time_interval = parameters["max_time_interval"] if "max_time_interval" in parameters else 0
    p_u_missing = parameters["p_u_missing"] if "p_u_missing" in parameters else 0
    for trace in log:
        for i in range(0, len(trace)):
            if random.random() < p_u_time:
                # print(str(i) + '###BEFORE###' + str(trace[i]))
                this_timestamp = int(((np.datetime64(trace[i]["time:timestamp"]) - np.datetime64(0, 's')) / np.timedelta64(1, 's')))
                [int_start, int_end] = generate_time_interval(this_timestamp, max_time_interval)
                trace[i]["u:time:timestamp_left"] = np.datetime64(int_start, "s")
                trace[i]["u:time:timestamp_right"] = np.datetime64(int_end, "s")
                # print(str(i) + '###AFTER###' + str(trace[i]))
            if random.random() < p_u_activity:
                trace[i]["u:concept:name"] = {"value": None, "children": {}}
                trace[i]["u:concept:name"]["children"][trace[i]["concept:name"]] = 0
                other_activities = [label for label in act_labels if label != trace[i]["concept:name"]]
                for label in random.sample(other_activities, n_u_activity - 1):
                    trace[i]["u:concept:name"]["children"][label] = 0
            if random.random() < p_u_missing:
                trace[i]["u:missing"] = 1


if __name__ == '__main__':
    from pm4py.objects.log.importer.xes import factory as xes_import_factory
    from proved.algorithms.conformance.alignments.utils import construct_behavior_graph_transitive_reduction
    from pm4py.algo.filtering.log.attributes.attributes_filter import get_attribute_values

    log = xes_import_factory.apply("event_log.xes")
    act_labels = get_attribute_values(log, 'concept:name')

    probabilities_u_time = [0, .1, .2, .3, .4]
    for p_u_time in probabilities_u_time:
        log = xes_import_factory.apply("event_log.xes")
        print("Log size:" + str(len(log)))
        introduce_uncertainty(log, act_labels, parameters={'p_u_time': p_u_time})
        a = time.time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        print("Time improved method for p=" + str(p_u_time))
        print(time.time()-a)
        b = time.time()
        for trace in log:
            construct_behavior_graph_transitive_reduction(trace)
        print("Time old method for p=" + str(p_u_time))
        print(time.time() - b)
