from copy import copy, deepcopy
from random import random, choice, sample, seed
from time import process_time
import datetime
import csv
import os
import glob
from collections import defaultdict
import statistics

from pm4py.algo.simulation.tree_generator import factory as treegen
from pm4py.objects.process_tree import semantics
from pm4py.objects.conversion.process_tree import factory as pt_conv_factory
import pm4py.objects.log.util.xes as xes_key
from pm4py.objects.log.util import sorting
# from pm4py.objects.petri.importer import factory as pnml_importer
import matplotlib.pyplot as plt
from matplotlib import rc
rc('text', usetex=True)

from proved.simulation.bewilderer.add_activities import add_uncertain_activities_to_log
from proved.simulation.bewilderer.add_timestamps import add_uncertain_timestamp_to_log
from proved.simulation.bewilderer.add_indeterminate_events import add_indeterminate_events_to_log
from proved.simulation.bewilderer.add_uncertainty import add_uncertainty
from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net
from proved.algorithms.conformance.alignments.alignment_bounds_su import cost_bounds_su_log, exec_alignment_lower_bound_su_log_bruteforce, exec_alignment_lower_bound_su_log

seed(123456)

# ALIGNMENTS_MEMO = {}

# Fixes on functions of this version of PM4Py library
import pm4py.objects.log.log as log_instance
from pm4py.objects.petri import semantics
def apply_playout(net, initial_marking, final_marking, no_traces=100, max_trace_length=100, trace_key=xes_key.DEFAULT_TRACEID_KEY, activity_key=xes_key.DEFAULT_NAME_KEY, timestamp_key=xes_key.DEFAULT_TIMESTAMP_KEY):
    """
    Do the playout of a Petrinet generating a log

    Parameters
    ----------
    net
        Petri net to play-out
    initial_marking
        Initial marking of the Petri net
    final_marking
        Final marking of the Petri net
    no_traces
        Number of traces to generate
    max_trace_length
        Maximum number of events per trace (do break)
    """
    # assigns to each event an increased timestamp from 1970
    curr_timestamp = 10000000
    log = log_instance.EventLog()
    for i in range(no_traces):
        trace = log_instance.Trace()
        trace.attributes[trace_key] = str(i)
        marking = copy(initial_marking)
        while len(trace) < max_trace_length:
            if not semantics.enabled_transitions(net, marking):  # supports nets with possible deadlocks
                break
            all_enabled_trans = semantics.enabled_transitions(net, marking)
            if marking == final_marking:
                trans = choice(tuple(all_enabled_trans.union({None})))
            else:
                trans = choice(tuple(all_enabled_trans))
            if trans is None:
                break
            if trans.label is not None:
                event = log_instance.Event()
                event[activity_key] = trans.label
                event[timestamp_key] = datetime.datetime.fromtimestamp(curr_timestamp)
                trace.append(event)
                # increases by 1 second
                curr_timestamp += 1
            marking = semantics.execute(trans, net, marking)
        log.append(trace)
    return log

import os
import time

from lxml import etree

from pm4py.objects import petri
from pm4py.objects.petri.common import final_marking
from pm4py.objects.random_variables.random_variable import RandomVariable
def import_net(input_file_path, return_stochastic_information=False, parameters=None):
    """
    Import a Petri net from a PNML file

    Parameters
    ----------
    input_file_path
        Input file path
    return_stochastic_information
        Enables return of stochastic information if found in the PNML
    parameters
        Other parameters of the algorithm
    """
    if parameters is None:
        parameters = {}

    tree = etree.parse(input_file_path)
    root = tree.getroot()

    net = petri.petrinet.PetriNet('imported_' + str(time.time()))
    marking = petri.petrinet.Marking()
    fmarking = petri.petrinet.Marking()

    nett = None
    page = None
    finalmarkings = None

    stochastic_information = {}

    for child in root:
        nett = child

    places_dict = {}
    trans_dict = {}

    if nett is not None:
        for child in nett:
            if "page" in child.tag:
                page = child
            if "finalmarkings" in child.tag:
                finalmarkings = child

    if page is None:
        page = nett

    if page is not None:
        for child in page:
            if "place" in child.tag:
                place_id = child.get("id")
                place_name = place_id
                number = 0
                for child2 in child:
                    if "name" in child2.tag:
                        for child3 in child2:
                            if child3.text:
                                place_name = child3.text
                    if "initialMarking" in child2.tag:
                        for child3 in child2:
                            if "text" in child3.tag:
                                number = int(child3.text)
                places_dict[place_id] = petri.petrinet.PetriNet.Place(place_id)
                net.places.add(places_dict[place_id])
                if number > 0:
                    marking[places_dict[place_id]] = number
                del place_name

    if page is not None:
        for child in page:
            if "transition" in child.tag:
                trans_name = child.get("id")
                trans_label = trans_name
                trans_visible = True

                random_variable = None

                for child2 in child:
                    if "name" in child2.tag:
                        for child3 in child2:
                            if child3.text:
                                if trans_label == trans_name:
                                    trans_label = child3.text
                    if "toolspecific" in child2.tag:
                        tool = child2.get("tool")
                        if "ProM" in tool:
                            activity = child2.get("activity")
                            if "invisible" in activity:
                                trans_visible = False
                        elif "StochasticPetriNet" in tool:
                            distribution_type = None
                            distribution_parameters = None
                            priority = None
                            weight = None

                            for child3 in child2:
                                key = child3.get("key")
                                value = child3.text

                                if key == "distributionType":
                                    distribution_type = value
                                elif key == "distributionParameters":
                                    distribution_parameters = value
                                elif key == "priority":
                                    priority = int(value)
                                elif key == "weight":
                                    weight = float(value)

                            if return_stochastic_information:
                                random_variable = RandomVariable()
                                random_variable.read_from_string(distribution_type, distribution_parameters)
                                random_variable.set_priority(priority)
                                random_variable.set_weight(weight)
                if not trans_visible:
                    trans_label = None
                #if "INVISIBLE" in trans_label:
                #    trans_label = None

                trans_dict[trans_name] = petri.petrinet.PetriNet.Transition(trans_name, trans_label)
                net.transitions.add(trans_dict[trans_name])

                if random_variable is not None:
                    stochastic_information[trans_dict[trans_name]] = random_variable

    if page is not None:
        for child in page:
            if "arc" in child.tag:
                arc_source = child.get("source")
                arc_target = child.get("target")

                if arc_source in places_dict and arc_target in trans_dict:
                    petri.utils.add_arc_from_to(places_dict[arc_source], trans_dict[arc_target], net)
                elif arc_target in places_dict and arc_source in trans_dict:
                    petri.utils.add_arc_from_to(trans_dict[arc_source], places_dict[arc_target], net)

    if finalmarkings is not None:
        for child in finalmarkings:
            for child2 in child:
                place_id = child2.get("idref")
                for child3 in child2:
                    if "text" in child3.tag:
                        number = int(child3.text)
                        if number > 0:
                            fmarking[places_dict[place_id]] = number

    # generate the final marking in the case has not been found
    if len(fmarking) == 0:
        fmarking = final_marking.discover_final_marking(net)

    if return_stochastic_information and len(list(stochastic_information.keys())) > 0:
        return net, marking, fmarking, stochastic_information

    return net, marking, fmarking


def add_deviations_montecarlo(log, p_a=0.0, p_s=0.0, p_d=0.0, activity_key=xes_key.DEFAULT_NAME_KEY, timestamp_key=xes_key.DEFAULT_TIMESTAMP_KEY):
    # Receives a log, and the probabilities to add deviations
    # p_a: probability of changing the activity label
    # p_s: probability of swapping timestamps between events
    # p_d: probability of adding an extra event

    for trace in log:

        # Adding deviations on activities: alters the activity labels with a certain probability
        if p_a > 0.0:
            # Fetching the alphabet of activity labels
            label_set = set()
            for event in trace:
                label_set.add(event[activity_key])
            for event in trace:
                if random() < p_a:
                    event[activity_key] = choice(list(label_set - {event[activity_key]}))

        # Adding swaps: swaps consecutive events with a certain probability
        if p_s > 0.0:
            for i in range(len(trace) - 1):
                if random() < p_s:
                    temp = trace[i][timestamp_key]
                    trace[i][timestamp_key] = trace[i + 1][timestamp_key]
                    trace[i + 1][timestamp_key] = temp

        # Adding extra events: duplicates events with a certain probability
        if p_d > 0.0:
            to_add = 0
            while random() < p_d and to_add < len(trace):
                to_add += 1
            events_to_add = [deepcopy(trace[i]) for i in sample(range(len(trace)), to_add)]
            for event in events_to_add:
                event[timestamp_key] += datetime.timedelta(milliseconds=1)
            for event in events_to_add:
                trace.append(event)

        return sorting.sort_timestamp(log)


def add_deviations(log, p_a=0.0, p_s=0.0, p_d=0.0, activity_key=xes_key.DEFAULT_NAME_KEY, timestamp_key=xes_key.DEFAULT_TIMESTAMP_KEY):
    # Receives a log, and the percentage of noisy events to alter
    # p_a: percentage of events with altered activity label
    # p_s: percentage of swapped timestamps
    # p_d: percentage of added extra events

    # Compiling a map of events in the event log and fetching the alphabet of activity labels
    # Saves separately indices for swaps (excludes the last event in a trace)
    log_map = {}
    label_set = set()
    indices_for_swaps = set()
    i = 0
    for trace in log:
        for j in range(len(trace)):
            log_map[i] = (trace, j)
            label_set.add(trace[j][activity_key])
            # If the event is not the last in the trace
            if j < len(trace) - 1:
                indices_for_swaps.add(i)
            i += 1

    # Adding deviations on activities: alters the activity labels
    if p_a > 0.0:
        to_alter = max(0, round(len(log_map) * p_a))
        indices_to_alter = sample(frozenset(log_map), to_alter)
        for i in indices_to_alter:
            trace, j = log_map[i]
            trace[j][activity_key] = choice(list(label_set - {trace[j][activity_key]}))

    # Adding swaps: swaps consecutive events with a certain probability
    if p_s > 0.0:
        to_swap = max(0, min(round(len(log_map) * p_s), len(indices_for_swaps)))
        indices_to_swap = sample(indices_for_swaps, to_swap)
        for i in indices_to_swap:
            trace, j = log_map[i]
            temp = trace[j][timestamp_key]
            trace[j][timestamp_key] = trace[j + 1][timestamp_key]
            trace[j + 1][timestamp_key] = temp

    # Adding extra events: duplicates events with a certain probability
    if p_d > 0.0:
        to_add = max(0, round(len(log_map) * p_d))
        indices_to_add = sample(frozenset(log_map), to_add)
        for i in indices_to_add:
            trace, j = log_map[i]
            new_event = deepcopy(trace[j])
            new_event[timestamp_key] += datetime.timedelta(milliseconds=1)
            trace.append(new_event)

    return label_set, log_map, sorting.sort_timestamp(log)


# def time_test(data_quantitative):
#     timing_naive = []
#     timing_improved = []
#     for ((net, im, fm), log) in data_quantitative:
#         timing_naive_current = 0
#         timing_improved_current = 0
#         for trace in log:
#             bn = behavior_net.BehaviorNet(behavior_graph.BehaviorGraph(trace))
#             t = time.process_time()
#             alignment_lower_bound_su_trace_bruteforce(bn, bn.initial_marking, bn.final_marking, net, im, fm)
#             timing_naive_current += time.process_time() - t
#             t = time.process_time()
#             alignment_lower_bound_su_trace(bn, bn.initial_marking, bn.final_marking, net, im, fm)
#             timing_improved_current += time.process_time() - t
#         timing_naive.append(timing_naive_current)
#         timing_improved.append(timing_improved_current)
#
#     return timing_naive, timing_improved


# def experiment_qualitative(net, im, fm, log, unc_a, unc_t, unc_i, dev_a=0.0, dev_s=0.0, dev_d=0.0, filename='', activity_key=xes_key.DEFAULT_NAME_KEY):
#     label_set = set()
#     for trace in log:
#         for event in trace:
#             label_set.add(event[activity_key])
#     # Adding deviations
#     _, log_map, log = add_deviations(log, dev_a, dev_s, dev_d)
#     # print(log)
#     # print(log_map)
#     uncertain_logs = []
#     for i in range(len(unc_a)):
#         uncertain_log = deepcopy(log)
#         # Adding uncertainty
#         if unc_a[i] > 0.0:
#             # print('Before')
#             # print(uncertain_log[0])
#             # print(unc_a[i])
#             # add_uncertain_activities_to_log(unc_a[i], uncertain_log, log_map=log_map, label_set=label_set)
#             add_uncertain_activities_to_log(unc_a[i], uncertain_log, label_set=label_set)
#             # print('After')
#             # print(uncertain_log[0])
#         if unc_t[i] > 0.0:
#             # add_uncertain_timestamp_to_log(unc_t[i], uncertain_log, log_map=log_map)
#             add_uncertain_timestamp_to_log(unc_t[i], uncertain_log)
#         if unc_i[i] > 0.0:
#             # add_indeterminate_events_to_log(unc_i[i], uncertain_log, log_map=log_map)
#             add_indeterminate_events_to_log(unc_i[i], uncertain_log)
#         print('Experiment: ' + filename + ', deviation = ' + str(dev_a) + ' ' + str(dev_s) + ' ' + str(dev_d) + ', uncertainty = ' + str(unc_a[i]) + ' ' + str(unc_t[i]) + ' ' + str(unc_i[i]))
#         uncertain_logs.append(uncertain_log)
#     results = [alignment_bounds_su_log(uncertain_logs[i], net, im, fm, parameters={'ALIGNMENTS_MEMO': ALIGNMENTS_MEMO}) for i in range(len(unc_a))]
#     # print(results)
#     lower_bound_list = []
#     upper_bound_list = []
#     for result in results:
#         sum_trace_dev_lb = 0
#         sum_trace_dev_ub = 0
#         for trace_result in result:
#             sum_trace_dev_lb += trace_result[0]['cost'] // 10000
#             # sum_trace_dev_ub += trace_result[1]['cost'] // 10000
#             sum_trace_dev_ub += trace_result[1] // 10000
#         lower_bound_list.append(sum_trace_dev_lb)
#         upper_bound_list.append(sum_trace_dev_ub)
#         # print('lower_bound_list')
#         # print(lower_bound_list)
#         # print('upper_bound_list')
#         # print(upper_bound_list)
#     return lower_bound_list, upper_bound_list


# def experiment_quantitative(data_quantitative, unc_a=0.0, unc_t=0.0, unc_i=0.0, activity_key=xes_key.DEFAULT_NAME_KEY):
#     for (_, uncertain_log) in data_quantitative:
#         log_map = {}
#         i = 0
#         for trace in uncertain_log:
#             for j in range(len(trace)):
#                 log_map[i] = (trace, j)
#                 i += 1
#
#         # Adding uncertainty
#         if unc_a > 0.0:
#             label_set = set()
#             for trace in uncertain_log:
#                 for event in trace:
#                     label_set.add(event[activity_key])
#             add_uncertain_activities_to_log(unc_a, uncertain_log, log_map=log_map, label_set=label_set)
#         if unc_t > 0.0:
#             add_uncertain_timestamp_to_log(unc_t, uncertain_log, log_map=log_map)
#         if unc_i > 0.0:
#             add_indeterminate_events_to_log(unc_i, uncertain_log, log_map=log_map)
#
#     return time_test(data_quantitative)


def experiments_average(results):
    sum_series1 = [0] * len(results[0][0])
    sum_series2 = [0] * len(results[0][1])
    for series1, series2 in results:
        for i in range(len(series1)):
            sum_series1[i] += series1[i]
        for i in range(len(series2)):
            sum_series2[i] += series2[i]
    return [value/len(results) for value in sum_series1], [value/len(results) for value in sum_series2]


# def run_tests():
#     parameters = {'mode': 8, 'min': 8, 'max': 9, 'parallel': .1, 'loop': .1}
#     # trees = [treegen.apply(parameters=parameters), treegen.apply(parameters=parameters), treegen.apply(parameters=parameters)]
#     # data_qualitative = [(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=250)) for tree in trees]
#     # data_quantitative = [(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=100)) for tree in trees]
#     # print(experiment_quantitative(data_quantitative, FIXED_PROB, FIXED_PROB, FIXED_PROB))
#     tree = treegen.apply(parameters=parameters)
#     # print(tree)
#     net, im, fm = pt_conv_factory.apply(tree)
#     log = semantics.generate_log(tree, no_traces=5)
#     # print(experiment_qualitative(net, im, fm, log, [.1, .2], [.1, .2], [.1, .2], .3, .3, .3))
#     print(experiment_qualitative(net, im, fm, log, [.1, .2, .3], [.1, .2, .3], [.1, .2, .3], .2, .2, .2))
#     # print(experiment_qualitative(net, im, fm, log, [.5], [.5], [.5]))
#     # TODO: pass the log in copy/deepcopy for tests!
#
#
# def preliminary_plots():
#     # QUALITATIVE EXPERIMENTS
#     ntests = 10
#     ntraces = 100
#     parameters = {'mode': 5, 'min': 5, 'max': 6, 'parallel': .1, 'loop': .1}
#     uncertainty = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
#     zeroes = [0] * 7
#
#     with open('qual_exps.csv', 'w', newline='') as csvfile:
#         writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
#
#         # Activity
#         writer.writerow(['Activity'])
#         writer.writerow([str(n) for n in uncertainty*2])
#         for i in range(ntests):
#             tree = treegen.apply(parameters=parameters)
#             net, im, fm = pt_conv_factory.apply(tree)
#             log = semantics.generate_log(tree, no_traces=ntraces)
#             writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .2, .2, .2)])
#         writer.writerow([])
#
#         # Timestamp
#         writer.writerow(['Timestamp'])
#         writer.writerow([str(n) for n in uncertainty*2])
#         for i in range(ntests):
#             tree = treegen.apply(parameters=parameters)
#             net, im, fm = pt_conv_factory.apply(tree)
#             log = semantics.generate_log(tree, no_traces=ntraces)
#             writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .2, .2, .2)])
#         writer.writerow([])
#
#         # Indeterminate events
#         writer.writerow(['Indet'])
#         writer.writerow([str(n) for n in uncertainty*2])
#         for i in range(ntests):
#             tree = treegen.apply(parameters=parameters)
#             net, im, fm = pt_conv_factory.apply(tree)
#             log = semantics.generate_log(tree, no_traces=ntraces)
#             writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .2, .2, .2)])
#         writer.writerow([])
#
#         # All
#         writer.writerow(['All'])
#         writer.writerow([str(n) for n in uncertainty*2])
#         for i in range(ntests):
#             tree = treegen.apply(parameters=parameters)
#             net, im, fm = pt_conv_factory.apply(tree)
#             log = semantics.generate_log(tree, no_traces=ntraces)
#             writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .2, .2, .2)])
#         writer.writerow([])
#
#     # QUANTITIVE EXPERIMENTS
#     ntests = 10
#     ntraces = 50
#     prob_uncertainty = .25
#     parameters = []
#     for i in range(5):
#         parameters.append({'mode': i+2, 'min': i+2, 'max': i+3, 'parallel': .1, 'loop': .1})
#     trees = [treegen.apply(parameters=p) for p in parameters]
#
#     with open('quant_exps.csv', 'w', newline='') as csvfile:
#         writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
#
#         # Activity
#         writer.writerow(['Activity'])
#         for i in range(ntests):
#             writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], prob_uncertainty, 0, 0)])
#         writer.writerow([])
#
#         # Timestamp
#         writer.writerow(['Timestamp'])
#         for i in range(ntests):
#             writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], 0, prob_uncertainty, 0)])
#         writer.writerow([])
#
#         # Indeterminate events
#         writer.writerow(['Indet'])
#         for i in range(ntests):
#             writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], 0, 0, prob_uncertainty)])
#         writer.writerow([])
#
#         # All
#         writer.writerow(['All'])
#         for i in range(ntests):
#             writer.writerow([str(n) for n in experiment_quantitative([(pt_conv_factory.apply(tree), semantics.generate_log(tree, no_traces=ntraces)) for tree in trees], prob_uncertainty, prob_uncertainty, prob_uncertainty)])
#         writer.writerow([])
#
#
# def preliminary_plots2():
#     # QUALITATIVE EXPERIMENTS
#     ntests = 5
#     ntraces = 100
#     parameters = {'mode': 6, 'min': 6, 'max': 7, 'parallel': .15, 'loop': .15}
#     uncertainty = [0, 0.05, 0.1, 0.15, 0.2, 0.25]
#     zeroes = [0] * len(uncertainty)
#
#     # with open('qual_exps.csv', 'w', newline='') as csvfile:
#     #     writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
#
#     # Activity
#     # writer.writerow(['Activity'])
#     # writer.writerow([str(n) for n in uncertainty * 2])
#     activity_results = []
#     for i in range(ntests):
#         tree = treegen.apply(parameters=parameters)
#         net, im, fm = pt_conv_factory.apply(tree)
#         log = semantics.generate_log(tree, no_traces=ntraces)
#         print('activity start')
#         activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .3, 0, 0))
#         print('activity 1')
#         activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, 0, .3, 0))
#         print('activity 2')
#         activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, 0, 0, .05))
#         print('activity 3')
#         activity_results.append(experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .3, .3, .05))
#         print('activity 4')
#     #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, zeroes, zeroes, .3, .3, .3)])
#     # writer.writerow([])
#
#     # Timestamp
#     # writer.writerow(['Timestamp'])
#     # writer.writerow([str(n) for n in uncertainty * 2])
#     timestamp_results = []
#     for i in range(ntests):
#         tree = treegen.apply(parameters=parameters)
#         net, im, fm = pt_conv_factory.apply(tree)
#         log = semantics.generate_log(tree, no_traces=ntraces)
#         print('timestamp start')
#         timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .3, 0, 0))
#         print('timestamp 1')
#         timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, 0, .3, 0))
#         print('timestamp 2')
#         timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, 0, 0, .05))
#         print('timestamp 3')
#         timestamp_results.append(experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .3, .3, .05))
#         print('timestamp 4')
#     #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, uncertainty, zeroes, .3, .3, .3)])
#     # writer.writerow([])
#
#     # Indeterminate events
#     # writer.writerow(['Indet'])
#     # writer.writerow([str(n) for n in uncertainty * 2])
#     indeterminate_results = []
#     for i in range(ntests):
#         tree = treegen.apply(parameters=parameters)
#         net, im, fm = pt_conv_factory.apply(tree)
#         log = semantics.generate_log(tree, no_traces=ntraces)
#         print('indeterminate start')
#         indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .3, 0, 0))
#         print('indeterminate 1')
#         indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, 0, .3, 0))
#         print('indeterminate 2')
#         indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, 0, 0, .05))
#         print('indeterminate 3')
#         indeterminate_results.append(experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .3, .3, .05))
#         print('indeterminate 4')
#     #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, zeroes, zeroes, uncertainty, .3, .3, .3)])
#     # writer.writerow([])
#
#     # All
#     # writer.writerow(['All'])
#     # writer.writerow([str(n) for n in uncertainty * 2])
#     all_results = []
#     for i in range(ntests):
#         tree = treegen.apply(parameters=parameters)
#         net, im, fm = pt_conv_factory.apply(tree)
#         log = semantics.generate_log(tree, no_traces=ntraces)
#         print('all start')
#         all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .4, 0, 0))
#         print('all 1')
#         all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, 0, .4, 0))
#         print('all 2')
#         all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, 0, 0, .05))
#         print('all 3')
#         all_results.append(experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .4, .4, .05))
#         print('all 4')
#     #     writer.writerow([str(n) for n in experiment_qualitative(net, im, fm, log, uncertainty, uncertainty, uncertainty, .3, .3, .3)])
#     # writer.writerow([])
#
#     import pickle
#     results = activity_results, timestamp_results, indeterminate_results, all_results
#     with open('qualitative_results.pickle', 'wb') as f:
#         pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)


# def preliminary_plots3():
#     # QUALITATIVE EXPERIMENTS
#     # ntraces = 100
#     ntraces = 100
#     # parameters = {'mode': 6, 'min': 6, 'max': 7, 'parallel': .15, 'loop': .15}
#     # uncertainty = [0, .05, .1, .15, .2, .25, .3, .35, .4]
#     uncertainty = [0, .05, .1, .15, .2, .25, .3]
#     zeroes = [0] * len(uncertainty)
#     uncertainty_types = ((uncertainty, zeroes, zeroes), (zeroes, uncertainty, zeroes), (zeroes, zeroes, uncertainty), (uncertainty, uncertainty, uncertainty))
#     # print(uncertainty_types)
#     deviation_types = ((.3, 0, 0), (0, .3, 0), (0, 0, .3), (.3, .3, .3))
#     # deviation_types = ((0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0))
#     net_size = 10
#     # nets_files = [glob.glob(os.path.join('experiments', 'models_new_exported', 'net' + str(net_size), '*.pnml'))[0]]
#     nets_files = sorted(glob.glob(os.path.join('experiments', 'models_new_exported', 'net' + str(net_size), '*.pnml')))
#     # nets_files = [os.path.join('experiments', 'models_new_exported', 'net10', 'net10_1.pnml')]
#     model_data = []
#     for net_file in nets_files:
#         net, im, fm = import_net(net_file)
#         model_data.append((net, im, fm))
#         ALIGNMENTS_MEMO[id(net)] = {}
#
#     qualitative_results = []
#     with open('full_exp_qual.csv', 'w', newline='') as csvfile:
#         writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
#         for unc_act, unc_time, unc_indet in uncertainty_types:
#             deviations_test_results = []
#             for dev_act, dev_swaps, dev_extra in deviation_types:
#                 one_run_results = []
#                 writer.writerow(['# Tests with uncertainty ' + str(unc_act) + ' ' + str(unc_time) + ' ' + str(unc_indet) + ' ' + ' and deviation ' + str(dev_act) + ' ' + str(dev_swaps) + ' ' + str(dev_extra) + ' #'])
#                 for i, this_model_data in enumerate(model_data):
#                     net, im, fm = this_model_data
#                     # print('Places')
#                     # print(net.places)
#                     # print('Transitions')
#                     # print(net.transitions)
#                     # print('Initial marking')
#                     # print(im)
#                     # print('Final marking')
#                     # print(fm)
#                     log = apply_playout(net, im, fm, no_traces=ntraces)
#                     # print('Log length')
#                     # print(len(log))
#                     # print('Trace')
#                     # print([event for event in log[0]])
#                     result = experiment_qualitative(net, im, fm, log, unc_act, unc_time, unc_indet, dev_act, dev_swaps, dev_extra, str(i))
#                     writer.writerow(result[0] + result[1])
#                     one_run_results.append(result)
#                 # print('One run results')
#                 # print(one_run_results)
#                 run_average = experiments_average(one_run_results)
#                 deviations_test_results.append(run_average)
#             qualitative_results.append(deviations_test_results)
#
#     # Pickling results
#     import pickle
#     with open('qualitative_results.pickle', 'wb') as f:
#         pickle.dump(qualitative_results, f, pickle.HIGHEST_PROTOCOL)
#
#     # Plotting
#     uncertainty_labels = ('Activities', 'Timestamp', 'Indeterminate events', 'All')
#     deviation_labels = ('Activity labels', 'Swaps', 'Extra events', 'All')
#     fig, plots = plt.subplots(len(qualitative_results[0]), len(qualitative_results), sharex='col', sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
#     # fig.suptitle('Qualitative experiments on synthetic data')
#     for i in range(len(qualitative_results)):
#         for j in range(len(qualitative_results[i])):
#             plots[j][i].plot(uncertainty, qualitative_results[i][j][0], c='b')
#             plots[j][i].plot(uncertainty, qualitative_results[i][j][1], c='r')
#             # Labels with relative values
#             for k, point in enumerate(qualitative_results[i][j][0]):
#                 if k > 0:
#                     plots[j][i].annotate(round(point / qualitative_results[i][j][0][0] * 100, 2), xy=(uncertainty[k], qualitative_results[i][j][0][k]), xytext=(-25, -15), textcoords='offset pixels', annotation_clip=False, size=10)
#             for k, point in enumerate(qualitative_results[i][j][1]):
#                 if k > 0:
#                     plots[j][i].annotate(round(point / qualitative_results[i][j][1][0] * 100, 2), xy=(uncertainty[k], qualitative_results[i][j][1][k]), xytext=(-25, 5), textcoords='offset pixels', annotation_clip=False, size=10)
#
#             if i == len(qualitative_results) - 1:
#                 plots[i][j].set_xlabel(uncertainty_labels[j])
#             if j == 0:
#                 plots[i][j].set_ylabel(deviation_labels[i])
#
#             plots[i][j].margins(y=.15)
#
#     for diagram in plots.flat:
#         diagram.label_outer()
#
#     plt.show()
#     plt.savefig('plot')


def generate_data_series_qualitative(uncertainty_values, experiment_results):
    lower_bound_series = [0] * len(uncertainty_values)
    upper_bound_series = [0] * len(uncertainty_values)
    for one_model_experiment_results in experiment_results.values():
        for i, uncertainty_value_result in enumerate(one_model_experiment_results):
            for trace_lower_bound, trace_upper_bound in uncertainty_value_result:
                lower_bound_series[i] += trace_lower_bound // 10000
                upper_bound_series[i] += trace_upper_bound // 10000
    return [series_value / len(experiment_results) for series_value in lower_bound_series], [series_value / len(experiment_results) for series_value in upper_bound_series]


def multidict():
    return defaultdict(dict)


def qualitative_experiments():
    # QUALITATIVE EXPERIMENTS
    # ntraces = 100
    uncertainty_values = (0, .04, .08, .12, .16)
    # uncertainty_values = (0, .03, .06, .09, .12)
    zeroes = tuple([0] * len(uncertainty_values))
    uncertainty_types = {'Activities': (uncertainty_values, zeroes, zeroes), 'Timestamps': (zeroes, uncertainty_values, zeroes), 'Indeterminate events': (zeroes, zeroes, uncertainty_values), 'All': (uncertainty_values, uncertainty_values, uncertainty_values)}
    deviation_types = {'Activity labels': (.3, 0, 0), 'Swaps': (0, .3, 0), 'Extra events': (0, 0, .3), 'All': (.3, .3, .3)}
    # net_size = 10
    # nets_files = sorted(glob.glob(os.path.join('models', 'net' + str(net_size), '*.pnml')))
    # model_data = [import_net(net_file) for net_file in nets_files]
    #
    # qualitative_results = defaultdict(multidict)
    # # realizations_results = defaultdict(multidict)
    #
    # for i, this_model_data in enumerate(model_data):
    #     net, im, fm = this_model_data
    #     log = apply_playout(net, im, fm, no_traces=ntraces)
    #     ALIGNMENTS_MEMO = {}
    #     for deviation_type, deviations in deviation_types.items():
    #         dev_a, dev_s, dev_d = deviations
    #         # Adding deviations
    #         label_set, _, dev_log = add_deviations(deepcopy(log), dev_a, dev_s, dev_d)
    #         for uncertainty_type, uncertainties in uncertainty_types.items():
    #             unc_act_values, unc_time_values, unc_indet_values = uncertainties
    #             qualitative_results[deviation_type][uncertainty_type][this_model_data] = []
    #             for j in range(len(unc_act_values)):
    #                 # Adding uncertainty
    #                 uncertain_log = deepcopy(dev_log)
    #                 add_uncertainty(unc_act_values[j], unc_time_values[j], unc_indet_values[j], uncertain_log, label_set=label_set)
    #                 print('Experiment: ' + str(i) + ', deviation = ' + str(dev_a) + ' ' + str(dev_s) + ' ' + str(dev_d) + ', uncertainty = ' + str(unc_act_values[j]) + ' ' + str(unc_time_values[j]) + ' ' + str(unc_indet_values[j]))
    #                 qualitative_results[deviation_type][uncertainty_type][this_model_data].append(cost_bounds_su_log(uncertain_log, net, im, fm, parameters={'ALIGNMENTS_MEMO': ALIGNMENTS_MEMO}))

    # # Pickling results
    # import pickle
    # with open('serv_qualitative_results_new.pickle', 'wb') as f:
    #     pickle.dump((uncertainty_values, qualitative_results), f, pickle.HIGHEST_PROTOCOL)
    import pickle
    with open(os.path.join('experiments', 'serv_qualitative_results_new.pickle'), 'rb') as f:
        uncertainty_values, qualitative_results = pickle.load(f)

    # Plotting
    fig, plots = plt.subplots(len(deviation_types), len(uncertainty_types), sharex='col', sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, deviation_type in enumerate(deviation_types):
        for j, uncertainty_type in enumerate(uncertainty_types):
            lower_bound_series, upper_bound_series = generate_data_series_qualitative(uncertainty_values, qualitative_results[deviation_type][uncertainty_type])
            plots[i][j].plot(uncertainty_values, [lower_bound_series[0]] * len(lower_bound_series), '#b0b0b0')
            plots[i][j].plot(uncertainty_values, lower_bound_series, ':b')
            plots[i][j].plot(uncertainty_values, upper_bound_series, '--r')
            # Labels with relative values
            for k, point in enumerate(lower_bound_series):
                if k > 0:
                    plots[i][j].annotate(round(point / lower_bound_series[0] * 100, 2), xy=(uncertainty_values[k], lower_bound_series[k]), xytext=(-25, -15), textcoords='offset pixels', annotation_clip=False, size=10)
            for k, point in enumerate(upper_bound_series):
                if k > 0:
                    plots[i][j].annotate(round(point / upper_bound_series[0] * 100, 2), xy=(uncertainty_values[k], upper_bound_series[k]), xytext=(-25, 5), textcoords='offset pixels', annotation_clip=False, size=10)

            # plots[i][j].annotate(deviation_type + '-' + uncertainty_type + '_' + str(i) + '-' + str(j), xy=(0, lower_bound_series[0]), annotation_clip=False, size=12)

            if i == len(qualitative_results) - 1:
                plots[i][j].set_xlabel(uncertainty_type)
            if j == 0:
                plots[i][j].set_ylabel(deviation_type)

            plots[i][j].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.51, 0.03, 'Uncertainty (type and percentage)', ha='center', fontsize=14)
    fig.text(0.075, 0.5, 'Conformance cost', va='center', rotation='vertical', fontsize=14)

    plt.show()
    plt.savefig('plot_qual')


def generate_data_series_quantitative_mean(net_sizes, experiment_results):
    bruteforce_time_series = [0] * len(net_sizes)
    improved_time_series = [0] * len(net_sizes)
    for i, net_size in enumerate(net_sizes):
        for one_net_run_time in experiment_results[net_size]:
            bruteforce_time_series[i] += one_net_run_time[0]
            improved_time_series[i] += one_net_run_time[1]
    return [series_value / len(experiment_results[net_sizes[0]]) for series_value in bruteforce_time_series], [series_value / len(experiment_results[net_sizes[0]]) for series_value in improved_time_series]


def generate_data_series_quantitative_median(net_sizes, experiment_results):
    bruteforce_time_series = [0] * len(net_sizes)
    improved_time_series = [0] * len(net_sizes)
    for i, net_size in enumerate(net_sizes):
        bruteforce_time_list, improved_time_list = tuple(zip(*experiment_results[net_size]))
        bruteforce_time_series[i] = statistics.median(bruteforce_time_list)
        improved_time_series[i] = statistics.median(improved_time_list)
        # for one_net_run_time in experiment_results[net_size]:
        #     bruteforce_time_series[i] += one_net_run_time[0]
        #     improved_time_series[i] += one_net_run_time[1]
    # return [series_value / len(experiment_results[net_sizes[0]]) for series_value in bruteforce_time_series], [series_value / len(experiment_results[net_sizes[0]]) for series_value in improved_time_series]
    return bruteforce_time_series, improved_time_series


def quantitative_experiments():
    # QUANTITATIVE EXPERIMENTS
    ntraces = 100
    uncertainty_value = .05
    uncertainty_types = {'Activities': (uncertainty_value, 0, 0), 'Timestamps': (0, uncertainty_value, 0), 'Indeterminate events': (0, 0, uncertainty_value), 'All': (uncertainty_value, uncertainty_value, uncertainty_value)}
    # net_sizes = [5, 10, 15, 20, 25]
    net_sizes = [5, 10, 15, 20]
    nets_map = {net_size: [import_net(net_file) for net_file in sorted(glob.glob(os.path.join('models', 'net' + str(net_size), '*.pnml')))] for net_size in net_sizes}
    # nets_map = {net_size: [import_net(net_file) for net_file in [sorted(glob.glob(os.path.join('experiments', 'models', 'net' + str(net_size), '*.pnml')))[9]]] for net_size in net_sizes}

    # Nets is a dictionary where the key is an integer (the size of the net), and the value is a list of 3-uples with net, initial marking and final marking

    # quantitative_results = defaultdict(dict)
    #
    # for uncertainty_type, uncertainty in uncertainty_types.items():
    #     unc_act_value, unc_time_value, unc_indet_value = uncertainty
    #     print('Testing uncertainty values: ' + str(unc_act_value) + ' ' + str(unc_time_value) + ' ' + str(unc_indet_value))
    #     for net_size, nets in nets_map.items():
    #         print('Testing net size: ' + str(net_size))
    #         quantitative_results[uncertainty_type][net_size] = []
    #         i = 0
    #         for net, im, fm in nets:
    #             print('Testing net: ' + str(i))
    #             log = apply_playout(net, im, fm, no_traces=ntraces)
    #             add_uncertainty(unc_act_value, unc_time_value, unc_indet_value, log)
    #             a = process_time()
    #             exec_alignment_lower_bound_su_log_bruteforce(log, net, im, fm)
    #             b = process_time()
    #             exec_alignment_lower_bound_su_log(log, net, im, fm)
    #             c = process_time()
    #             quantitative_results[uncertainty_type][net_size].append((b - a, c - b))
    #             i += 1
    #
    # # Pickling results
    # import pickle
    # with open('serv_quantitative_results.pickle', 'wb') as f:
    #     pickle.dump((uncertainty_value, quantitative_results), f, pickle.HIGHEST_PROTOCOL)
    import pickle
    with open(os.path.join('experiments', '__serv_quantitative_results.pickle'), 'rb') as f:
        uncertainty_values, quantitative_results = pickle.load(f)

    # Plotting averages
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_mean(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b')
        plots[i].plot(net_sizes, improved_time_series, '--r')
        plots[i].set_xlabel(uncertainty_type)
        if i == 0:
            plots[i].set_ylabel('Mean time (seconds)')

        plots[i].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Uncertainty (type and percentage)', ha='center', fontsize=14)

    plt.show()
    plt.savefig('plot_mean')

    fig.clf()
    # Plotting medians
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_median(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b')
        plots[i].plot(net_sizes, improved_time_series, '--r')
        plots[i].set_xlabel(uncertainty_type)
        if i == 0:
            plots[i].set_ylabel('Median time (seconds)')

        plots[i].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Uncertainty (type and percentage)', ha='center', fontsize=14)

    plt.show()
    plt.savefig('plot_median')

    fig.clf()
    # Plotting averages (log)
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_mean(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b')
        plots[i].plot(net_sizes, improved_time_series, '--r')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].set_yscale('log')
        if i == 0:
            plots[i].set_ylabel('Mean time (seconds)')

        plots[i].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Uncertainty (type and percentage)', ha='center', fontsize=14)

    plt.show()
    plt.savefig('plot_mean_log')

    fig.clf()
    # Plotting medians (log)
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_median(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b')
        plots[i].plot(net_sizes, improved_time_series, '--r')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].set_yscale('log')
        if i == 0:
            plots[i].set_ylabel('Median time (seconds)')

        plots[i].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Uncertainty (type and percentage)', ha='center', fontsize=14)

    plt.show()
    plt.savefig('plot_median_log')

    fig.clf()


# from pm4py.objects.petri.petrinet import Marking
# from pm4py.objects.petri.exporter import factory as pnml_exporter
# def shitfix():
#     folders = ['5', '10', '15', '20', '25', '30', '35', '40']
#     start_place = ['n9', 'n18', 'n31', 'n36', 'n45', 'n54', 'n63', 'n74']
#     end_place = ['n10', 'n19', 'n32', 'n37', 'n46', 'n55', 'n64', 'n75']
#     for i, folder in enumerate(folders):
#         nets_full_paths = glob.iglob(os.path.join('experiments', 'models', 'net' + folder, '*.pnml'))
#         destination_folder = os.path.join('experiments', 'models_exported', 'net' + folder)
#         for net_full_path in nets_full_paths:
#             net, _, _ = import_net(net_full_path)
#             net_file_name = os.path.basename(net_full_path)
#             initial_marking = Marking()
#             final_marking = Marking()
#             for place in net.places:
#                 if place.name == start_place[i]:
#                     initial_marking[place] = 1
#                 if place.name == end_place[i]:
#                     final_marking[place] = 1
#             pnml_exporter.apply(net, initial_marking, os.path.join(destination_folder, net_file_name), final_marking=final_marking)
#
#
# def shitfix_folder(folder, start_places, end_places):
#     print(start_places)
#     print(end_places)
#     from pm4py.objects.petri.petrinet import Marking
#     from pm4py.objects.petri.exporter import factory as pnml_exporter
#     for i in range(10):
#         net_full_path = os.path.join('experiments', 'models', 'net' + folder, 'net' + folder + '_' + str(i+1) + '.pnml')
#         net_file_name = os.path.basename(net_full_path)
#         print(net_file_name)
#         destination_folder = os.path.join('experiments', 'models_new_exported', 'net' + folder)
#         net, _, _ = import_net(net_full_path)
#         initial_marking = Marking()
#         final_marking = Marking()
#         for place in net.places:
#             if place.name == start_places[i]:
#                 initial_marking[place] = 1
#             if place.name == end_places[i]:
#                 final_marking[place] = 1
#         pnml_exporter.apply(net, initial_marking, os.path.join(destination_folder, net_file_name), final_marking=final_marking)


# def preprocess_log_elisabetta():
#     import pandas as pd
#     from pm4py.objects.conversion.log import converter as log_converter
#
#     log_csv = pd.read_csv('<path_to_csv_file.csv>', sep=',')
#     trace_attributes = ('C02_IDUNIVOCOASSISTITO', 'ETA_ACCESSO', 'C03_CODICEPRESIDIO', 'C04_CODICECENTROPS', 'C05_ACCESSO', 'C05B_PATOLOGIA_TRIAGE', 'C06_DIAGNOSI_PRINCIPALE', 'C07_ESITO_DIMISSIONE')
#     for trace_attribute in trace_attributes:
#         log_csv.rename(columns={trace_attribute: 'case:' + trace_attribute}, inplace=True)
#     parameters = {log_converter.Variants.TO_EVENT_LOG.value.Parameters.CASE_ID_KEY: 'C01_IDUNIVOCOEPISODIO'}
#     event_log = log_converter.apply(log_csv, parameters=parameters, variant=log_converter.Variants.TO_EVENT_LOG)


# def replot():
#
#     uncertainty = [0, .05, .1, .15, .2]
#
#     # Loading results
#     import pickle
#     with open('_qualitative_results.pickle', 'rb') as f:
#         qualitative_results = pickle.load(f)
#
#     # Plotting
#     uncertainty_labels = ('Activities', 'Timestamp', 'Indeterminate events', 'All')
#     deviation_labels = ('Activity labels', 'Swaps', 'Extra events', 'All')
#     fig, plots = plt.subplots(len(qualitative_results[0]), len(qualitative_results), sharex='col', sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
#     # fig.suptitle('Qualitative experiments on synthetic data')
#     # handles = labels = None
#     for i in range(len(qualitative_results)):
#         for j in range(len(qualitative_results[i])):
#             plots[j][i].plot(uncertainty, qualitative_results[i][j][0], c='b')
#             plots[j][i].plot(uncertainty, qualitative_results[i][j][1], c='r')
#             # Labels with relative values
#             for k, point in enumerate(qualitative_results[i][j][0]):
#                 if k > 0:
#                     plots[j][i].annotate(round(point / qualitative_results[i][j][0][0] * 100, 2), xy=(uncertainty[k], qualitative_results[i][j][0][k]), xytext=(-25, -15), textcoords='offset pixels', annotation_clip=False, size=10)
#             for k, point in enumerate(qualitative_results[i][j][1]):
#                 if k > 0:
#                     plots[j][i].annotate(round(point / qualitative_results[i][j][1][0] * 100, 2), xy=(uncertainty[k], qualitative_results[i][j][1][k]), xytext=(-25, 5), textcoords='offset pixels', annotation_clip=False, size=10)
#
#             if i == len(qualitative_results) - 1:
#                 plots[i][j].set_xlabel(uncertainty_labels[j])
#             if j == 0:
#                 plots[i][j].set_ylabel(deviation_labels[i])
#
#             plots[i][j].margins(y=.15)
#             # handles, labels = plots[i][j].get_legend_handles_labels()
#
#     for diagram in plots.flat:
#         diagram.label_outer()
#
#     # l1 = ax1.plot(x, y1, color="red")[0]
#     # l2 = ax2.plot(x, y2, color="green")[0]
#     # fig.legend([l1, l2, l3, l4],  # The line objects
#     #            labels=line_labels,  # The labels for each line
#     #            loc="center right",  # Position of legend
#     #            borderaxespad=0.1,  # Small spacing around legend box
#     #            title="Legend Title"  # Title for the legend
#     #            )
#     # fig.legend(handles, labels, loc='upper center')
#     plt.show()


def replot_qualitative():
    # Loading results
    import pickle
    with open('serv_qualitative_results_new.pickle', 'rb') as f:
        uncertainty_values, qualitative_results = pickle.load(f)

    deviation_types = tuple(qualitative_results)
    uncertainty_types = tuple(qualitative_results[deviation_types[0]])

    # Plotting
    fig, plots = plt.subplots(len(deviation_types), len(uncertainty_types), sharex='col', sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, deviation_type in enumerate(deviation_types):
        for j, uncertainty_type in enumerate(uncertainty_types):
            lower_bound_series, upper_bound_series = generate_data_series_qualitative(uncertainty_values, qualitative_results[deviation_type][uncertainty_type])
            plots[i][j].plot(uncertainty_values, lower_bound_series, c='b')
            plots[i][j].plot(uncertainty_values, upper_bound_series, c='r')
            # Labels with relative values
            for k, point in enumerate(lower_bound_series):
                if k > 0:
                    plots[i][j].annotate(round(point / lower_bound_series[0] * 100, 2), xy=(uncertainty_values[k], lower_bound_series[k]), xytext=(-25, -15), textcoords='offset pixels', annotation_clip=False, size=10)
            for k, point in enumerate(upper_bound_series):
                if k > 0:
                    plots[i][j].annotate(round(point / upper_bound_series[0] * 100, 2), xy=(uncertainty_values[k], upper_bound_series[k]), xytext=(-25, 5), textcoords='offset pixels', annotation_clip=False, size=10)

            # plots[i][j].annotate(deviation_type + '-' + uncertainty_type + '_' + str(i) + '-' + str(j), xy=(0, lower_bound_series[0]), annotation_clip=False, size=12)

            if i == len(qualitative_results) - 1:
                plots[i][j].set_xlabel(uncertainty_type)
            if j == 0:
                plots[i][j].set_ylabel(deviation_type)

            plots[i][j].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    plt.show()
    plt.savefig('plot')


if __name__ == '__main__':
    # # run_tests()
    # # print(experiments_average([([1, 3, 5], [6, 7]), ([2, 4, 6], [7, 8]), ([3, 5, 7], [8, 9])]))
    # # preliminary_plots2()
    # parameters = {'mode': 5, 'min': 5, 'max': 6, 'parallel': .15, 'loop': .15}
    # # for i in range(10):
    # tree = treegen.apply(parameters=parameters)
    # net, im, fm = pt_conv_factory.apply(tree)
    # print('Number of transitions = ' + str(len(net.transitions)))
    # log = semantics.generate_log(tree, no_traces=1)
    # for trace in log:
    #     print('Trace:')
    #     for event in trace:
    #         print(event)
    # # log = add_deviations(log, p_a=.0, p_s=.0, p_d=.0)
    # add_indeterminate_events_to_log(.25, log)
    # print('*********************************************')
    # for trace in log:
    #     print('Trace:')
    #     for event in trace:
    #         print(event)

    # Plotting tests
    # uncertainty = [0, 1, 2]
    # qualitative_results = [[([0, 1, 2], [3, 4, 5]), ([6, 7, 8], [9, 10, 11])], [([12, 13, 14], [15, 16, 17]), ([18, 19, 20], [21, 22, 23])], [([24, 25, 26], [27, 28, 29]), ([30, 31, 32], [33, 34, 35])]]
    #
    # uncertainty_types = ('Activities', 'Timestamp', 'Indeterminate events', 'All')
    #
    # import matplotlib.pyplot as plt
    # fig, subplots = plt.subplots(len(qualitative_results), len(qualitative_results[0]), sharex='col', sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    # for i in range(len(qualitative_results)):
    #     for j in range(len(qualitative_results[i])):
    #         subplots[i][j].plot(uncertainty, qualitative_results[i][j][0], c='b')
    #         subplots[i][j].plot(uncertainty, qualitative_results[i][j][1], c='r')
    #         if i == len(qualitative_results) - 1:
    #             subplots[i][j].set_xlabel('Bottom ' + str(j))
    #         if j == 0:
    #             subplots[i][j].set_ylabel('Left ' + str(i))
    #
    # for subplot in subplots.flat:
    #     subplot.label_outer()
    #
    # plt.show()

    qualitative_experiments()
    # quantitative_experiments()

    # replot_qualitative()



    # net, im, fm = import_net(os.path.join('experiments', 'models_exported', 'net5', 'net05_1.pnml'))
    # print('Places')
    # print(net.places)
    # print('Transitions')
    # print(net.transitions)
    # print('Initial marking')
    # print(im)
    # print('Final marking')
    # print(fm)
    # from pm4py.visualization.petrinet import factory as pt_vis
    # gviz = pt_vis.apply(net, im, fm)
    # pt_vis.view(gviz)
    # log = apply_playout(net, im, fm, no_traces=1)
    # trace = log[0]
    # print([event['concept:name'] for event in trace])
    # from proved.artifacts.behavior_net import behavior_net as behavior_net_builder
    #
    # behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))
    # print('BN Places')
    # print(behavior_net.places)
    # print('BN Transitions')
    # print(behavior_net.transitions)
    # print('BN Initial marking')
    # print(behavior_net.initial_marking)
    # print('BN Final marking')
    # print(behavior_net.final_marking)
    # gviz = pt_vis.apply(behavior_net, behavior_net.initial_marking, behavior_net.final_marking)
    # pt_vis.view(gviz)

    # shitfix_folder('5', ['n7', 'n7', 'n9', 'n7', 'n5', 'n7', 'n7', 'n7', 'n9', 'n7'], ['n8', 'n8', 'n10', 'n8', 'n6', 'n8', 'n8', 'n8', 'n10', 'n8'])
    # shitfix_folder('10', ['n16', 'n18', 'n16', 'n18', 'n16', 'n16', 'n16', 'n16', 'n16', 'n16'], ['n17', 'n19', 'n17', 'n19', 'n17', 'n17', 'n17', 'n17', 'n17', 'n17'])
    # shitfix_folder('15', ['n25', 'n29', 'n29', 'n25', 'n23', 'n25', 'n25', 'n25', 'n29', 'n25'], ['n26', 'n30', 'n30', 'n26', 'n24', 'n26', 'n26', 'n26', 'n30', 'n26'])
    # shitfix_folder('20', ['n38', 'n38', 'n38', 'n36', 'n30', 'n38', 'n38', 'n38', 'n38', 'n38'], ['n39', 'n39', 'n39', 'n37', 'n31', 'n39', 'n39', 'n39', 'n39', 'n39'])
    # shitfix_folder('25', ['n43', 'n47', 'n49', 'n43', 'n37', 'n43', 'n43', 'n43', 'n49', 'n43'], ['n44', 'n48', 'n50', 'n44', 'n38', 'n44', 'n44', 'n44', 'n50', 'n44'])
    # shitfix_folder('30', ['n52', 'n56', 'n62', 'n50', 'n50', 'n46', 'n52', 'n52', 'n62', 'n52'], ['n53', 'n57', 'n63', 'n51', 'n51', 'n47', 'n53', 'n53', 'n63', 'n53'])
    # shitfix_folder('35', ['n65', 'n69', 'n73', 'n82', 'n53', 'n65', 'n65', 'n65', 'n73', 'n65'], ['n66', 'n70', 'n74', 'n83', 'n54', 'n66', 'n66', 'n66', 'n74', 'n6']) FIX FIX FIX FIX
    # shitfix_folder('40', ['n74', 'n76', 'n80', 'n66', 'n62', 'n74', 'n74', 'n74', 'n80', 'n74'], ['n75', 'n77', 'n81', 'n67', 'n63', 'n75', 'n75', 'n75', 'n81', 'n75'])
