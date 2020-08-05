from copy import copy, deepcopy
from random import random, choice, sample, seed
from time import process_time
import datetime
import csv
import os
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
            t.append(Event({'concept:name': 'a', 'time:timestamp': basetime + timedelta(seconds=j)}))
        log.append(t)

    if p_u_time:
        timevariation = timedelta(milliseconds=1500)

        for trace in log:
            for event in trace:
                if random.random() < p_u_time:
                    event["u:time:timestamp_left"] = event['time:timestamp'] - timevariation
                    event["u:time:timestamp_right"] = event['time:timestamp'] + timevariation
    return log


def generate_data_series(net_sizes, experiment_results):
    bruteforce_time_series = [0] * len(net_sizes)
    improved_time_series = [0] * len(net_sizes)
    for i, net_size in enumerate(net_sizes):
        for one_net_run_time in experiment_results[net_size]:
            bruteforce_time_series[i] += one_net_run_time[0]
            improved_time_series[i] += one_net_run_time[1]
    return [series_value / len(experiment_results[net_sizes[0]]) for series_value in bruteforce_time_series], [series_value / len(experiment_results[net_sizes[0]]) for series_value in improved_time_series]


def conformance_checking_experiments():
    # EXPERIMENTS WITH CONFORMANCE CHECKING
    ntraces = 1
    uncertainty_value = .2
    uncertainty_types = {'Activities': (uncertainty_value, 0, 0), 'Timestamps': (0, uncertainty_value, 0), 'Indeterminate events': (0, 0, uncertainty_value), 'All': (uncertainty_value, uncertainty_value, uncertainty_value)}
    net_sizes = [5, 10, 15]
    # print(sorted(glob.glob(os.path.join('experiments', 'models', 'net' + '5', '*.pnml'))))
    # nets_map = {net_size: [import_net(net_file) for net_file in sorted(glob.glob(os.path.join('experiments', 'models', 'net' + str(net_size), '*.pnml')))] for net_size in net_sizes}
    nets_map = {net_size: [import_net(net_file) for net_file in [sorted(glob.glob(os.path.join('experiments', 'models', 'net' + str(net_size), '*.pnml')))[9]]] for net_size in net_sizes}
    # print(sorted(glob.glob(os.path.join('experiments', 'models', 'net5', '*.pnml')))[9])
    # for net_size, nets in nets_map.items():
    #     print('NET ' + str(net_size))
    #     for net, im, fm in nets:
    #         print(str(net))
    #         print(str(im))
    #         print(str(fm))


    # Nets is a dictionary where the key is an integer (the size of the net), and the value is a list of 3-uples with net, initial marking and final marking

    quantitative_results = defaultdict(dict)

    for uncertainty_type, uncertainty in uncertainty_types.items():
        unc_act_value, unc_time_value, unc_indet_value = uncertainty
        for net_size, nets in nets_map.items():
            quantitative_results[uncertainty_type][net_size] = []
            for net, im, fm in nets:
                log = apply_playout(net, im, fm, no_traces=ntraces)
                # from pm4py.visualization.petrinet import factory as pt_vis
                # gviz = pt_vis.apply(net, im, fm)
                # pt_vis.view(gviz)
                # for trace in log:
                #     print([event['concept:name'] for event in trace])
                add_uncertainty(unc_act_value, unc_time_value, unc_indet_value, log)
                a = process_time()
                exec_alignment_lower_bound_su_log_bruteforce(log, net, im, fm)
                b = process_time()
                exec_alignment_lower_bound_su_log(log, net, im, fm)
                c = process_time()
                quantitative_results[uncertainty_type][net_size].append((b - a, c - b))

    # Pickling results
    import pickle
    with open('quantitative_results.pickle', 'wb') as f:
        pickle.dump((uncertainty_value, quantitative_results), f, pickle.HIGHEST_PROTOCOL)

    # Plotting
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, c='b')
        plots[i].plot(net_sizes, improved_time_series, c='r')
        # Labels with relative values
        # for j, point in enumerate(lower_bound_series):
        #     if j > 0:
        #         plots[i].annotate(round(point / lower_bound_series[0] * 100, 2), xy=(uncertainty_values[j], lower_bound_series[j]), xytext=(-25, -15), textcoords='offset pixels', annotation_clip=False, size=10)
        # for j, point in enumerate(upper_bound_series):
        #     if j > 0:
        #         plots[i].annotate(round(point / upper_bound_series[0] * 100, 2), xy=(uncertainty_values[j], upper_bound_series[j]), xytext=(-25, 5), textcoords='offset pixels', annotation_clip=False, size=10)

        # plots[i][j].annotate(deviation_type + '-' + uncertainty_type + '_' + str(i) + '-' + str(j), xy=(0, lower_bound_series[0]), annotation_clip=False, size=12)

        plots[i].set_xlabel(uncertainty_type)
        if i == 0:
            plots[i].set_ylabel('Time (seconds)')

        plots[i].margins(y=.15)

    for diagram in plots.flat:
        diagram.label_outer()

    plt.show()
