from copy import copy
from random import random, choice, sample
import time
import datetime

from pm4py.algo.simulation.playout.versions import basic_playout
from pm4py.algo.simulation.tree_generator import factory as treegen
from pm4py.objects.process_tree import semantics
from pm4py.objects.conversion.process_tree import factory as pt_conv_factory

import pm4py.objects.log.util.xes as xes_key
from proved.simulation.bewilderer.activities import add_uncertain_activities_to_log
from proved.simulation.bewilderer.timestamps import add_uncertain_timestamp_to_log_relative
from proved.simulation.bewilderer.indeterminate_events import add_indeterminate_events_to_log
from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net
from proved.algorithms.conformance.alignments.alignment_bounds_su import alignment_lower_bound_su_trace, alignment_lower_bound_su_trace_bruteforce, alignment_upper_bound_su_trace_bruteforce

random.seed(123456)

FIXED_PROB = .05


def add_deviations(log, p_a, p_s, p_d, activity_key=xes_key.DEFAULT_NAME_KEY, timestamp_key=xes_key.DEFAULT_TIMESTAMP_KEY):
    # Receives a log, and the probabilities to add deviations
    # p_a: probability of changing the activity label
    # p_s: probability of swapping timestamps between events
    # p_d: probability of adding an extra event

    # Fetching the alphabet of activity labels
    label_set = set()
    for trace in log:
        for event in trace:
            label_set.add(event[activity_key])

    for trace in log:

        # Adding deviations on activities
        for event in trace:
            if random() < p_a:
                event[activity_key] = choice(label_set - {event[activity_key]})

        #Adding swaps
        for i in range(len(trace) - 1):
            if random() < p_s:
                temp = trace[i][timestamp_key]
                trace[i][timestamp_key] = trace[i + 1][timestamp_key]
                trace[i + 1][timestamp_key] = temp

        # Adding extra events
        to_add = 0
        while random() < p_d and to_add < len(trace):
            to_add += 1
        events_to_add = [copy(trace[i]) for i in sample(range(trace), to_add)]
        for event in events_to_add:
            event[timestamp_key] += datetime.timedelta(seconds=1)
        trace += events_to_add

        log.sort()


def time_test(data_quantitative):
    timing_naive = []
    timing_improved = []
    for ((net, im, fm), log) in data_quantitative:
        timing_naive_current = 0
        timing_improved_current = 0
        for trace in log:
            bn = behavior_net.BehaviorNet(behavior_graph.BehaviorGraph(trace))
            t = time.process_time()
            alignment_lower_bound_su_trace_bruteforce(bn, bn.initial_marking, bn.final_marking, net, im, fm)
            timing_naive_current += time.process_time() - t
            t = time.process_time()
            alignment_lower_bound_su_trace(bn, bn.initial_marking, bn.final_marking, net, im, fm)
            timing_improved_current += time.process_time() - t
        timing_naive.append(timing_naive_current)
        timing_improved.append(timing_improved_current)

    return timing_naive, timing_improved


def experiment_qualitative_activity(data_qualitative):
    pass


def experiment_qualitative_timestamp(data_qualitative):
    pass


def experiment_qualitative_indeterminate_event(data_qualitative):
    pass


def experiment_qualitative_indeterminate_all(data_qualitative):
    pass


def experiment_quantitative(data_quantitative, p_a=0.0, p_t=0.0, p_i=0.0, activity_key=xes_key.DEFAULT_NAME_KEY):
    for (_, log) in data_quantitative:
        # Adding uncertainty
        if p_a > 0.0:
            label_set = set()
            for trace in log:
                for event in trace:
                    label_set.add(event[activity_key])
            add_uncertain_activities_to_log(log, p_a, label_set)
        if p_t > 0.0:
            add_uncertain_timestamp_to_log_relative(log, p_t, p_t)
        if p_i > 0.0:
            add_indeterminate_events_to_log(log, p_i)

    return time_test(data_quantitative)


def run_tests():
    # TODO: ask Alessandro for the recursion parameter
    trees = [treegen.apply(), treegen.apply(), treegen.apply()]
    data_qualitative = [(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=250)) for tree in trees]
    data_quantitative = [(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=100)) for tree in trees]
    print(experiment_quantitative(data_quantitative, FIXED_PROB, FIXED_PROB, FIXED_PROB))
    # TODO: da passare in copia!


if __name__ == '__main__':
    run_tests()
