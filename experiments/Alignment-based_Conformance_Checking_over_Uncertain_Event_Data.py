from copy import deepcopy
from random import random, choice, sample, seed
import time
import datetime
import csv

from pm4py.algo.simulation.playout.versions import basic_playout
from pm4py.algo.simulation.tree_generator import factory as treegen
from pm4py.objects.process_tree import semantics
from pm4py.objects.conversion.process_tree import factory as pt_conv_factory
import pm4py.objects.log.util.xes as xes_key
from pm4py.objects.log.util import sorting

from proved.simulation.bewilderer.add_activities import add_uncertain_activities_to_log
from proved.simulation.bewilderer.add_timestamps import add_uncertain_timestamp_to_log_relative
from proved.simulation.bewilderer.add_indeterminate_events import add_indeterminate_events_to_log
from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net
from proved.algorithms.conformance.alignments.alignment_bounds_su import alignment_bounds_su_log, alignment_bounds_su_trace, alignment_lower_bound_su_trace, alignment_lower_bound_su_trace_bruteforce, alignment_upper_bound_su_trace_bruteforce

seed(123456)

FIXED_PROB = .05


def add_deviations(log, p_a=0.0, p_s=0.0, p_d=0.0, activity_key=xes_key.DEFAULT_NAME_KEY, timestamp_key=xes_key.DEFAULT_TIMESTAMP_KEY):
    # Receives a log, and the probabilities to add deviations
    # p_a: probability of changing the activity label
    # p_s: probability of swapping timestamps between events
    # p_d: probability of adding an extra event

    # for trace in log:
    #     for event in trace:
    #         print(event)

    # Fetching the alphabet of activity labels
    # if p_a > 0.0:
    label_set = set()
    for trace in log:
        for event in trace:
            label_set.add(event[activity_key])

    for trace in log:

        # Adding deviations on activities: alters the activity labels with a certain probability
        # if p_a > 0.0:
        for event in trace:
            if random() < p_a:
                event[activity_key] = choice(list(label_set - {event[activity_key]}))

        # Adding swaps: swaps consecutive events with a certain probability
        # if p_s > 0.0:
        for i in range(len(trace) - 1):
            if random() < p_s:
                temp = trace[i][timestamp_key]
                trace[i][timestamp_key] = trace[i + 1][timestamp_key]
                trace[i + 1][timestamp_key] = temp

        # Adding extra events: duplicates events with a certain probability
        # if p_d > 0.0:
        to_add = 0
        while random() < p_d and to_add < len(trace):
            to_add += 1
        events_to_add = [deepcopy(trace[i]) for i in sample(range(len(trace)), to_add)]
        for event in events_to_add:
            event[timestamp_key] += datetime.timedelta(seconds=1)
        # trace += events_to_add # Does not work
        # trace.extend(events_to_add) # Does not work
        # TODO: find a more elegant way to do this
        for event in events_to_add:
            trace.append(event)

        return sorting.sort_timestamp(log)


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


def experiment_qualitative(net, im, fm, log, unc_a, unc_t, unc_i, dev_a=0.0, dev_s=0.0, dev_d=0.0, activity_key=xes_key.DEFAULT_NAME_KEY):
    # for (_, log) in data_qualitative:
    label_set = set()
    for trace in log:
        for event in trace:
            label_set.add(event[activity_key])
    # Adding deviations
    log = add_deviations(log, dev_a, dev_s, dev_d)
    uncertainlogs = []
    for i in range(len(unc_a)):
        # uncertainlog = deepcopy(log)
        # Adding deviations
        uncertainlog = deepcopy(log)
        # Adding uncertainty
        if unc_a[i] > 0.0:
            add_uncertain_activities_to_log(uncertainlog, unc_a[i], label_set)
        if unc_t[i] > 0.0:
            add_uncertain_timestamp_to_log_relative(uncertainlog, unc_t[i], unc_t[i])
        if unc_i[i] > 0.0:
            add_indeterminate_events_to_log(uncertainlog, unc_i[i])
        uncertainlogs.append(uncertainlog)

    # TODO: format rows before returning!
    results = [alignment_bounds_su_log(uncertainlogs[i], net, im, fm) for i in range(len(unc_a))]
    # results = alignment_bounds_su_trace(uncertainlogs[0][4], net, im, fm)
    lowerboundlist = []
    upperboundlist = []
    for result in results:
        sumtracedevlb = 0
        sumtracedevub = 0
        for traceresult in result:
            sumtracedevlb += traceresult[0]['cost'] // 10000
            sumtracedevub += traceresult[1]['cost'] // 10000
            # print('&&&&&&&&&&&&&&&&&&&&&&')
            # print(traceresult[0])
            # print(traceresult[1])
            # print('&&&&&&&&&&&&&&&&&&&&&&')
        lowerboundlist.append(sumtracedevlb)
        upperboundlist.append(sumtracedevub)
    return lowerboundlist, upperboundlist


def experiment_quantitative(data_quantitative, unc_a=0.0, unc_t=0.0, unc_i=0.0, activity_key=xes_key.DEFAULT_NAME_KEY):
    for (_, log) in data_quantitative:
        # Adding uncertainty
        if unc_a > 0.0:
            label_set = set()
            for trace in log:
                for event in trace:
                    label_set.add(event[activity_key])
            add_uncertain_activities_to_log(log, unc_a, label_set)
        if unc_t > 0.0:
            add_uncertain_timestamp_to_log_relative(log, unc_t, unc_t)
        if unc_i > 0.0:
            add_indeterminate_events_to_log(log, unc_i)

    return time_test(data_quantitative)


def experiments_average(results):
    sum_series1 = [0] * len(results[0][0])
    sum_series2 = [0] * len(results[0][1])
    for series1, series2 in results:
        for i in range(len(series1)):
            sum_series1[i] += series1[i]
        for i in range(len(series2)):
            sum_series2[i] += series2[i]
    return [value/len(results) for value in sum_series1], [value/len(results) for value in sum_series2]

def qualitative_output(results):
    pass


def quantitative_output(results):
    pass


def run_tests():
    parameters = {'mode': 8, 'min': 8, 'max': 9, 'parallel': .1, 'loop': .1}
    trees = [treegen.apply(parameters=parameters), treegen.apply(parameters=parameters), treegen.apply(parameters=parameters)]
    data_qualitative = [(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=250)) for tree in trees]
    data_quantitative = [(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=100)) for tree in trees]
    # print(experiment_quantitative(data_quantitative, FIXED_PROB, FIXED_PROB, FIXED_PROB))
    tree = treegen.apply(parameters=parameters)
    # print(tree)
    net, im, fm = pt_conv_factory.apply(tree)
    log = semantics.generate_log(tree, no_traces=5)
    # print(experiment_qualitative(net, im, fm, log, [.1, .2], [.1, .2], [.1, .2], .3, .3, .3))
    print(experiment_qualitative(net, im, fm, log, [.1, .2, .3], [.1, .2, .3], [.1, .2, .3], .2, .2, .2))
    # print(experiment_qualitative(net, im, fm, log, [.5], [.5], [.5]))
    # TODO: pass the log in copy/deepcopy for tests!

def preliminary_plots():
    ### QUALITATIVE EXPERIMENTS
    ntests = 10
    ntraces = 100
    parameters = {'mode': 5, 'min': 5, 'max': 6, 'parallel': .1, 'loop': .1}
    uncertainty = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
    zeroes = [0] * 7

    with open('qual_exps.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        # Activity
        writer.writerow(['Activity'])
        writer.writerow([str(n) for n in uncertainty*2])
        for i in range(ntests):
            tree = treegen.apply(parameters=parameters)
            net, im, fm = pt_conv_factory.apply(tree)
            log = semantics.generate_log(tree, no_traces=ntraces)
            writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .2, .2, .2)])
        writer.writerow([])

        # Timestamp
        writer.writerow(['Timestamp'])
        writer.writerow([str(n) for n in uncertainty*2])
        for i in range(ntests):
            tree = treegen.apply(parameters=parameters)
            net, im, fm = pt_conv_factory.apply(tree)
            log = semantics.generate_log(tree, no_traces=ntraces)
            writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .2, .2, .2)])
        writer.writerow([])

        # Indeterminate events
        writer.writerow(['Indet'])
        writer.writerow([str(n) for n in uncertainty*2])
        for i in range(ntests):
            tree = treegen.apply(parameters=parameters)
            net, im, fm = pt_conv_factory.apply(tree)
            log = semantics.generate_log(tree, no_traces=ntraces)
            writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .2, .2, .2)])
        writer.writerow([])

        # All
        writer.writerow(['All'])
        writer.writerow([str(n) for n in uncertainty*2])
        for i in range(ntests):
            tree = treegen.apply(parameters=parameters)
            net, im, fm = pt_conv_factory.apply(tree)
            log = semantics.generate_log(tree, no_traces=ntraces)
            writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .2, .2, .2)])
        writer.writerow([])

    ### QUANTITIVE EXPERIMENTS
    ntests = 10
    ntraces = 50
    prob_uncertainty = .25
    parameters = []
    for i in range(5):
        parameters.append({'mode': i+2, 'min': i+2, 'max': i+3, 'parallel': .1, 'loop': .1})
    trees = [treegen.apply(parameters=p) for p in parameters]

    with open('quant_exps.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        # Activity
        writer.writerow(['Activity'])
        for i in range(ntests):
            writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], prob_uncertainty, 0, 0)])
        writer.writerow([])

        # Timestamp
        writer.writerow(['Timestamp'])
        for i in range(ntests):
            writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], 0, prob_uncertainty, 0)])
        writer.writerow([])

        # Indeterminate events
        writer.writerow(['Indet'])
        for i in range(ntests):
            writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], 0, 0, prob_uncertainty)])
        writer.writerow([])

        # All
        writer.writerow(['All'])
        for i in range(ntests):
            writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], prob_uncertainty, prob_uncertainty, prob_uncertainty)])
        writer.writerow([])


def preliminary_plots2():
    ### QUALITATIVE EXPERIMENTS
    ntests = 5
    ntraces = 100
    parameters = {'mode': 4, 'min': 4, 'max': 5, 'parallel': .15, 'loop': .15}
    uncertainty = [0, 0.1, 0.15, 0.2, 0.25, 0.3]
    zeroes = [0] * 6

    # with open('qual_exps.csv', 'w', newline='') as csvfile:
    #     writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # Activity
    # writer.writerow(['Activity'])
    # writer.writerow([str(n) for n in uncertainty * 2])
    activity_results = []
    for i in range(ntests):
        tree = treegen.apply(parameters=parameters)
        net, im, fm = pt_conv_factory.apply(tree)
        log = semantics.generate_log(tree, no_traces=ntraces)
        print('activity start')
        activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .4, 0, 0))
        print('activity 1')
        activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, 0, .4, 0))
        print('activity 2')
        activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, 0, 0, .4))
        print('activity 3')
        activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .4, .4, .4))
        print('activity 4')
    #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .3, .3, .3)])
    # writer.writerow([])

    # Timestamp
    # writer.writerow(['Timestamp'])
    # writer.writerow([str(n) for n in uncertainty * 2])
    timestamp_results = []
    for i in range(ntests):
        tree = treegen.apply(parameters=parameters)
        net, im, fm = pt_conv_factory.apply(tree)
        log = semantics.generate_log(tree, no_traces=ntraces)
        print('timestamp start')
        timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .4, 0, 0))
        print('timestamp 1')
        timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, 0, .4, 0))
        print('timestamp 2')
        timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, 0, 0, .4))
        print('timestamp 3')
        timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .4, .4, .4))
        print('timestamp 4')
    #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .3, .3, .3)])
    # writer.writerow([])

    # Indeterminate events
    # writer.writerow(['Indet'])
    # writer.writerow([str(n) for n in uncertainty * 2])
    indeterminate_results = []
    for i in range(ntests):
        tree = treegen.apply(parameters=parameters)
        net, im, fm = pt_conv_factory.apply(tree)
        log = semantics.generate_log(tree, no_traces=ntraces)
        print('indeterminate start')
        indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .4, 0, 0))
        print('indeterminate 1')
        indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, 0, .4, 0))
        print('indeterminate 2')
        indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, 0, 0, .4))
        print('indeterminate 3')
        indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .4, .4, .4))
        print('indeterminate 4')
    #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .3, .3, .3)])
    # writer.writerow([])

    # All
    # writer.writerow(['All'])
    # writer.writerow([str(n) for n in uncertainty * 2])
    all_results = []
    for i in range(ntests):
        tree = treegen.apply(parameters=parameters)
        net, im, fm = pt_conv_factory.apply(tree)
        log = semantics.generate_log(tree, no_traces=ntraces)
        print('all start')
        all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .4, 0, 0))
        print('all 1')
        all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, 0, .4, 0))
        print('all 2')
        all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, 0, 0, .4))
        print('all 3')
        all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .4, .4, .4))
        print('all 4')
    #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .3, .3, .3)])
    # writer.writerow([])

    import pickle
    results = activity_results, timestamp_results, indeterminate_results, all_results
    with open('qualitative_results.pickle', 'wb') as f:
        pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    # run_tests()
    # print(experiments_average([([1, 3, 5], [6, 7]), ([2, 4, 6], [7, 8]), ([3, 5, 7], [8, 9])]))
    preliminary_plots2()
