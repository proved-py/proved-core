from copy import copy, deepcopy
from random import random, choice, sample, seed
from time import process_time
import datetime
import csv
import os
import sys
import glob
from collections import defaultdict
from datetime import datetime
from datetime import timedelta

from pm4py.algo.simulation.tree_generator import factory as treegen
from pm4py.objects.process_tree import semantics
from pm4py.objects.conversion.process_tree import factory as pt_conv_factory
import pm4py.objects.log.util.xes as xes_key
from pm4py.objects.log.util import sorting
from pm4py.objects.log.log import Trace, Event
from pm4py.objects.log.importer.xes import factory as xes_import_factory
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


def create_log(numtraces, lentraces, p_u_time):
    """
    Creates an event log with fixed-length traces, and all events have activity label 'a'.
    Timestamps are uncertain with some probability.
    :param numtraces: number of traces to be generated
    :param lentraces: length of the traces in the log
    :param p_u_time: probability of uncertain timestamp
    :return: an event log with uncertain timestamps
    """

    basetime = datetime.fromtimestamp(10000000)
    log = []
    for i in range(numtraces):
        t = Trace()
        for j in range(lentraces):
            t.append(Event({'concept:name': 'a', 'time:timestamp': basetime + timedelta(hours=j)}))
        log.append(t)

    add_uncertain_timestamp_to_log(p_u_time, log)
    # if p_u_time:
    #     timevariation = timedelta(milliseconds=1500)
    #
    #     for trace in log:
    #         for event in trace:
    #             if random() < p_u_time:
    #                 event["u:time:timestamp_left"] = event['time:timestamp'] - timevariation
    #                 event["u:time:timestamp_right"] = event['time:timestamp'] + timevariation
    return log


def generate_data_series(net_sizes, experiment_results):
    transitive_reduction_time_series = [0] * len(net_sizes)
    improved_time_series = [0] * len(net_sizes)
    multiset_improved_time_series = [0] * len(net_sizes)
    for i, net_size in enumerate(net_sizes):
        for one_net_run_time in experiment_results[net_size]:
            transitive_reduction_time_series[i] += one_net_run_time[0]
            improved_time_series[i] += one_net_run_time[1]
            multiset_improved_time_series += one_net_run_time[1]
    return [series_value / len(experiment_results[net_sizes[0]]) for series_value in transitive_reduction_time_series], [series_value / len(experiment_results[net_sizes[0]]) for series_value in improved_time_series], [series_value / len(experiment_results[net_sizes[0]]) for series_value in multiset_improved_time_series]


from proved.artifacts.behavior_graph import tr_behavior_graph, old_behavior_graph
from proved.artifacts.uncertain_log import uncertain_log
from proved.algorithms.conformance.alignments.alignment_bounds_su import alignment_lower_bound_su_trace

### EXPERIMENT PARAMS
# Common parameters
TR_LEGEND_LABEL = 'TrRed'
IMP_LEGEND_LABEL = 'Imp'
MULT_IMP_LEGEND_LABEL = 'ImpMul'
TR_PLOT_STYLE = '-b'
IMP_PLOT_STYLE = '--r'
MULT_IMP_PLOT_STYLE = '..g'
BPI_2012_PATH = os.path.join('experiments', 'BPI_Challenge_2012.xes')
HELPDESK_PATH = os.path.join('experiments', 'Help_Desk_event_log.xes')
ROAD_TRAFFIC_PATH = os.path.join('experiments', 'Road_Traffic_Fine_Management_Process.xes')
BPI_2012_LABEL = 'BPIC 2012'
HELPDESK_LABEL = 'HelpDesk'
ROAD_TRAFFIC_LABEL = 'RTFM'

# Experiment 1: Computing time against trace length
T1_N_TRACES = 100
T1_TRACE_LENGTH = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]
T1_UNCERTAINTY = .4

# Experiment 2: Computing time against uncertainty percentage
T2_N_TRACES = 100
T2_TRACE_LENGTH = 10
T2_UNCERTAINTY = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]

# Experiment 3: Memory occupation against log size
T3_N_TRACES = [100, 200, 300, 400, 500, 600, 700, 800]
T3_TRACE_LENGTH = 10
T3_UNCERTAINTY = .4

# Experiment 4: Conformance checking computing time against model size
T4_N_TRACES = 100
T4_NET_SIZES = [5, 10, 15]
T4_UNCERTAINTY = .1

# Experiment 5: Computing time against uncertainty percentage (real life)
T5_UNCERTAINTY = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]

# Experiment 6: Memory occupation against uncertainty percentage (real life)
T6_UNCERTAINTY = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]


def trace_length_vs_time():
    # Experiment 1: Computing time against trace length
    transitive_reduction_times = []
    improved_times = []
    multiset_improved_times = []
    for length in T1_TRACE_LENGTH:
        log = create_log(T1_N_TRACES, length, T1_UNCERTAINTY)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        transitive_reduction_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)
        a = process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        multiset_improved_times.append(process_time() - a)

    # Pickling results
    import pickle
    with open('exp1.pickle', 'wb') as f:
        pickle.dump((T4_UNCERTAINTY, (transitive_reduction_times, improved_times, multiset_improved_times)), f, pickle.HIGHEST_PROTOCOL)

    # Plotting
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(T2_UNCERTAINTY, transitive_reduction_times, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    ax.plot(T2_UNCERTAINTY, improved_times, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    ax.plot(T2_UNCERTAINTY, multiset_improved_times, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    ax.legend(frameon=False)
    plt.show()
    plt.clf()


def prob_uncertainty_vs_time():
    # Experiment 2: Computing time against uncertainty percentage
    transitive_reduction_times = []
    improved_times = []
    multiset_improved_times = []
    for p_u_time in T2_UNCERTAINTY:
        log = create_log(T2_N_TRACES, T2_TRACE_LENGTH, p_u_time)
        a = process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        transitive_reduction_times.append(process_time() - a)
        a = process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(process_time() - a)
        a = process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        multiset_improved_times.append(process_time() - a)

    # Pickling results
    import pickle
    with open('exp2.pickle', 'wb') as f:
        pickle.dump((T4_UNCERTAINTY, (transitive_reduction_times, improved_times, multiset_improved_times)), f, pickle.HIGHEST_PROTOCOL)

    # Plotting
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(T2_UNCERTAINTY, transitive_reduction_times, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    ax.plot(T2_UNCERTAINTY, improved_times, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    ax.plot(T2_UNCERTAINTY, multiset_improved_times, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    ax.legend(frameon=False)
    plt.show()
    plt.clf()


def log_size_vs_memory():
    # Experiment 3: Memory occupation against log size
    transitive_reduction_memory = []
    improved_memory = []
    multiset_improved_memory = []
    for n_traces in T3_N_TRACES:
        log = create_log(n_traces, T3_TRACE_LENGTH, T3_UNCERTAINTY)
        transitive_reduction_memory.append(sys.getsizeof([tr_behavior_graph.TRBehaviorGraph(trace) for trace in log]))
        improved_memory.append(sys.getsizeof([behavior_graph.BehaviorGraph(trace) for trace in log]))
        multiset_improved_memory.append(sys.getsizeof(uncertain_log.UncertainLog(log)))

    # Pickling results
    import pickle
    with open('exp3.pickle', 'wb') as f:
        pickle.dump((T4_UNCERTAINTY, (transitive_reduction_memory, improved_memory, multiset_improved_memory)), f, pickle.HIGHEST_PROTOCOL)

    # Plotting
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(T2_UNCERTAINTY, transitive_reduction_memory, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    ax.plot(T2_UNCERTAINTY, improved_memory, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    ax.plot(T2_UNCERTAINTY, multiset_improved_memory, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    ax.legend(frameon=False)
    plt.show()
    plt.clf()


def model_size_vs_conformance_checking_time_experiment():
    # Experiment 4: Conformance checking computing time against model size
    uncertainty_types = {'Activities': (T4_UNCERTAINTY, 0, 0), 'Timestamps': (0, T4_UNCERTAINTY, 0), 'Indeterminate events': (0, 0, T4_UNCERTAINTY), 'All': (T4_UNCERTAINTY, T4_UNCERTAINTY, T4_UNCERTAINTY)}
    nets_map = {net_size: [import_net(net_file) for net_file in [sorted(glob.glob(os.path.join('experiments', 'models', 'net' + str(net_size), '*.pnml')))[9]]] for net_size in T4_NET_SIZES}

    conformance_checking_results = defaultdict(dict)

    for uncertainty_type, uncertainty in uncertainty_types.items():
        unc_act_value, unc_time_value, unc_indet_value = uncertainty
        for net_size, nets in nets_map.items():
            conformance_checking_results[uncertainty_type][net_size] = []
            for net, im, fm in nets:
                log = apply_playout(net, im, fm, no_traces=T4_N_TRACES)
                add_uncertainty(unc_act_value, unc_time_value, unc_indet_value, log)
                a = process_time()
                for trace in log:
                    bg = tr_behavior_graph.TRBehaviorGraph(trace)
                    bn = behavior_net.BehaviorNet(bg)
                    alignment_lower_bound_su_trace(bn, bn.initial_marking, bn.final_marking, net, im, fm)
                b = process_time()
                for trace in log:
                    bg = old_behavior_graph.BehaviorGraph(trace)
                    bn = behavior_net.BehaviorNet(bg)
                    alignment_lower_bound_su_trace(bn, bn.initial_marking, bn.final_marking, net, im, fm)
                c = process_time()
                uncertain_log_object = uncertain_log.UncertainLog(log)
                for bg, _ in uncertain_log_object.behavior_graphs_map.values():
                    bn = behavior_net.BehaviorNet(bg)
                    alignment_lower_bound_su_trace(bn, bn.initial_marking, bn.final_marking, net, im, fm)
                d = process_time()
                conformance_checking_results[uncertainty_type][net_size].append((b - a, c - b, d - c))

    # Pickling results
    import pickle
    with open('exp4.pickle', 'wb') as f:
        pickle.dump((T4_UNCERTAINTY, conformance_checking_results), f, pickle.HIGHEST_PROTOCOL)

    # Plotting averages
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        transitive_reduction_time_series, improved_time_series, multiset_improved_time_series = generate_data_series(T4_NET_SIZES, conformance_checking_results[uncertainty_type])
        plots[i].plot(T4_NET_SIZES, transitive_reduction_time_series, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
        plots[i].plot(T4_NET_SIZES, improved_time_series, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
        plots[i].plot(T4_NET_SIZES, multiset_improved_time_series, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
        plots[i].set_xlabel(uncertainty_type)
        if i == 0:
            plots[i].set_ylabel('Mean time (seconds)')

        plots[i].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    plt.show()
    plt.savefig('plot_mean')


def perc_uncertainty_vs_time_rl():
    # Experiment 5: Computing time against uncertainty percentage (real life)
    bpi_transitive_reduction_times = []
    bpi_improved_times = []
    bpi_multiset_improved_times = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(BPI_2012_PATH)
        add_uncertain_timestamp_to_log(log, p_u_time)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        bpi_transitive_reduction_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        bpi_improved_times.append(time.process_time() - a)
        uncertain_log_object = uncertain_log.UncertainLog(log)
        bpi_multiset_improved_times.append(process_time() - a)

    hd_transitive_reduction_times = []
    hd_improved_times = []
    hd_multiset_improved_times = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(HELPDESK_PATH)
        add_uncertain_timestamp_to_log(log, p_u_time)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        hd_transitive_reduction_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        hd_improved_times.append(time.process_time() - a)
        uncertain_log_object = uncertain_log.UncertainLog(log)
        hd_multiset_improved_times.append(process_time() - a)

    rtfm_transitive_reduction_times = []
    rtfm_improved_times = []
    rtfm_multiset_improved_times = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(ROAD_TRAFFIC_PATH)
        add_uncertain_timestamp_to_log(log, p_u_time)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        rtfm_transitive_reduction_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        rtfm_improved_times.append(time.process_time() - a)
        uncertain_log_object = uncertain_log.UncertainLog(log)
        rtfm_multiset_improved_times.append(process_time() - a)

    # Plotting
    fig, plots = plt.subplots(ncols=3, sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    plots[0].set_ylabel('Mean time (seconds)')
    plots[0].set_xlabel(BPI_2012_LABEL)
    plots[1].set_xlabel(HELPDESK_LABEL)
    plots[2].set_xlabel(ROAD_TRAFFIC_LABEL)
    plots[0].margins(y=.15)
    plots[0].plot(T4_NET_SIZES, bpi_transitive_reduction_times, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[0].plot(T4_NET_SIZES, bpi_improved_times, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    plots[0].plot(T4_NET_SIZES, bpi_multiset_improved_times, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    plots[1].margins(y=.15)
    plots[1].plot(T4_NET_SIZES, hd_transitive_reduction_times, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[1].plot(T4_NET_SIZES, hd_improved_times, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    plots[1].plot(T4_NET_SIZES, hd_multiset_improved_times, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    plots[2].margins(y=.15)
    plots[2].plot(T4_NET_SIZES, rtfm_transitive_reduction_times, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[2].plot(T4_NET_SIZES, rtfm_improved_times, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    plots[2].plot(T4_NET_SIZES, rtfm_multiset_improved_times, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)

    for diagram in plots.flat:
        diagram.label_outer()

    plt.show()
    plt.savefig('plot_mean')


def perc_uncertainty_vs_memory_rl():
    # Experiment 6: Memory occupation against uncertainty percentage (real life)
    # Experiment 5: Computing time against uncertainty percentage (real life)
    bpi_transitive_reduction_memory = []
    bpi_improved_memory = []
    bpi_multiset_improved_memory = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(BPI_2012_PATH)
        add_uncertain_timestamp_to_log(log, p_u_time)
        bpi_transitive_reduction_memory.append(sys.getsizeof([tr_behavior_graph.TRBehaviorGraph(trace) for trace in log]))
        bpi_improved_memory.append(sys.getsizeof([behavior_graph.BehaviorGraph(trace) for trace in log]))
        bpi_multiset_improved_memory.append(sys.getsizeof(uncertain_log.UncertainLog(log)))

    hd_transitive_reduction_memory = []
    hd_improved_memory = []
    hd_multiset_improved_memory = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(HELPDESK_PATH)
        add_uncertain_timestamp_to_log(log, p_u_time)
        hd_transitive_reduction_memory.append(sys.getsizeof([tr_behavior_graph.TRBehaviorGraph(trace) for trace in log]))
        hd_improved_memory.append(sys.getsizeof([behavior_graph.BehaviorGraph(trace) for trace in log]))
        hd_multiset_improved_memory.append(sys.getsizeof(uncertain_log.UncertainLog(log)))

    rtfm_transitive_reduction_memory = []
    rtfm_improved_memory = []
    rtfm_multiset_improved_memory = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(ROAD_TRAFFIC_PATH)
        add_uncertain_timestamp_to_log(log, p_u_time)
        rtfm_transitive_reduction_memory.append(sys.getsizeof([tr_behavior_graph.TRBehaviorGraph(trace) for trace in log]))
        rtfm_improved_memory.append(sys.getsizeof([behavior_graph.BehaviorGraph(trace) for trace in log]))
        rtfm_multiset_improved_memory.append(sys.getsizeof(uncertain_log.UncertainLog(log)))

    # Plotting
    fig, plots = plt.subplots(ncols=3, sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    plots[0].set_ylabel('Memory (bytes)')
    plots[0].set_xlabel(BPI_2012_LABEL)
    plots[1].set_xlabel(HELPDESK_LABEL)
    plots[2].set_xlabel(ROAD_TRAFFIC_LABEL)
    plots[0].margins(y=.15)
    plots[0].plot(T4_NET_SIZES, bpi_transitive_reduction_memory, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[0].plot(T4_NET_SIZES, bpi_improved_memory, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    plots[0].plot(T4_NET_SIZES, bpi_multiset_improved_memory, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    plots[1].margins(y=.15)
    plots[1].plot(T4_NET_SIZES, hd_transitive_reduction_memory, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[1].plot(T4_NET_SIZES, hd_improved_memory, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    plots[1].plot(T4_NET_SIZES, hd_multiset_improved_memory, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    plots[2].margins(y=.15)
    plots[2].plot(T4_NET_SIZES, rtfm_transitive_reduction_memory, c=TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[2].plot(T4_NET_SIZES, rtfm_improved_memory, c=IMP_PLOT_STYLE, label=IMP_LEGEND_LABEL)
    plots[2].plot(T4_NET_SIZES, rtfm_multiset_improved_memory, c=MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)

    for diagram in plots.flat:
        diagram.label_outer()

    plt.show()
    plt.savefig('plot_mean')
