import random
import time
import csv

import numpy as np
from pm4py.algo.simulation.tree_generator import factory as tree_gen_factory
from pm4py.algo.filtering.log.attributes.attributes_filter import get_attribute_values
from pm4py.objects.process_tree import semantics

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
                this_timestamp = int(
                    ((np.datetime64(trace[i]["time:timestamp"]) - np.datetime64(0, 's')) / np.timedelta64(1, 's')))
                [int_start, int_end] = generate_time_interval(this_timestamp, max_time_interval)
                trace[i]["u:time:timestamp_left"] = np.datetime64(int_start, "s")
                trace[i]["u:time:timestamp_right"] = np.datetime64(int_end, "s")
            if random.random() < p_u_activity:
                trace[i]["u:concept:name"] = {"value": None, "children": {}}
                trace[i]["u:concept:name"]["children"][trace[i]["concept:name"]] = 0
                other_activities = [label for label in act_labels if label != trace[i]["concept:name"]]
                for label in random.sample(other_activities, n_u_activity - 1):
                    trace[i]["u:concept:name"]["children"][label] = 0
            if random.random() < p_u_missing:
                trace[i]["u:missing"] = 1


fixed_prob = .4
fixed_ntraces = 1000
fixed_length = 25


def probability_experiment(probs):
    naive_times = []
    improved_times = []
    for p_u_time in probs:
        parameters = {'mode': fixed_length, 'min': fixed_length - 1, 'max': fixed_length + 1, 'loop': .5, 'silent': 0}

        tree = tree_gen_factory.apply(parameters=parameters)
        log = semantics.generate_log(tree, no_traces=fixed_ntraces)

        act_labels = get_attribute_values(log, 'concept:name')

        unc_log = log
        introduce_uncertainty(unc_log, act_labels, parameters={'p_u_time': p_u_time})
        a = time.process_time()
        for trace in unc_log:
            bg = behavior_graph.TRBehaviorGraph(trace)
        # print(naive_times)
        naive_times.append(time.process_time() - a)
        # print(naive_times)
        a = time.process_time()
        for trace in unc_log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)

    return naive_times, improved_times


def ntraces_experiment(nstraces):
    naive_times = []
    improved_times = []
    for n in nstraces:
        parameters = {'mode': fixed_length, 'min': fixed_length - 1, 'max': fixed_length + 1, 'loop': .5, 'silent': 0}

        tree = tree_gen_factory.apply(parameters=parameters)
        log = semantics.generate_log(tree, no_traces=n)

        act_labels = get_attribute_values(log, 'concept:name')

        unc_log = log
        introduce_uncertainty(unc_log, act_labels, parameters={'p_u_time': fixed_prob})
        a = time.process_time()
        for trace in unc_log:
            bg = behavior_graph.TRBehaviorGraph(trace)
        naive_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in unc_log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)

    return naive_times, improved_times


def length_experiment(lengths):
    naive_times = []
    improved_times = []
    for length in lengths:
        parameters = {'mode': length, 'min': length - 1, 'max': length + 1, 'loop': .5, 'silent': 0}

        tree = tree_gen_factory.apply(parameters=parameters)
        log = semantics.generate_log(tree, no_traces=fixed_ntraces)

        act_labels = get_attribute_values(log, 'concept:name')

        unc_log = log
        introduce_uncertainty(unc_log, act_labels, parameters={'p_u_time': fixed_prob})
        a = time.process_time()
        for trace in unc_log:
            bg = behavior_graph.TRBehaviorGraph(trace)
        naive_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in unc_log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)

    return naive_times, improved_times


if __name__ == '__main__':
    probs = [0, .1, .2, .3, .4, .5, .6]
    nstraces = [10, 100, 1000, 10000, 100000, 1000000, 10000000]
    lengths = [10, 20, 30, 40, 50, 60, 70]

    random.seed(123456)

    ntests = 10

    probs_results = [probability_experiment(probs) for i in range(ntests)]
    with open('probs_results_naive.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
        csvwriter.writerow(probs)
        for line in probs_results:
            csvwriter.writerow(line[0])
    with open('probs_results_improved.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
        csvwriter.writerow(probs)
        for line in probs_results:
            csvwriter.writerow(line[1])

    ntraces_results = [ntraces_experiment(nstraces) for i in range(ntests)]
    with open('ntraces_results_naive.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
        csvwriter.writerow(nstraces)
        for line in ntraces_results:
            csvwriter.writerow(line[0])
    with open('ntraces_results_improved.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
        csvwriter.writerow(nstraces)
        for line in ntraces_results:
            csvwriter.writerow(line[1])

    length_results = [length_experiment(lengths) for i in range(ntests)]
    with open('lengths_results_naive.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
        csvwriter.writerow(lengths)
        for line in length_results:
            csvwriter.writerow(line[0])
    with open('lengths_results_improved.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
        csvwriter.writerow(lengths)
        for line in length_results:
            csvwriter.writerow(line[1])
