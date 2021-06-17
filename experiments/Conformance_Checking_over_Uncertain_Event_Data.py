import os
from copy import deepcopy
from random import choice, sample, seed
from time import process_time
import datetime
import glob
from collections import defaultdict
import statistics

import pm4py.objects.log.util.xes as xes_key
from pm4py.objects.log.util import sorting
import matplotlib.pyplot as plt
from matplotlib import rc
from numpy import mean

from experiments.utils import apply_playout, import_net

rc('text', usetex=True)

from proved.simulation.bewilderer.add_uncertainty import add_uncertainty
from proved.algorithms.conformance.alignments.alignment_bounds_su import cost_bounds_su_log, exec_alignment_lower_bound_su_log_bruteforce, exec_alignment_lower_bound_su_log, acyclic_net_variants_new
from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net as behavior_net_builder

seed(123456)


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
    ntraces = 100
    uncertainty_values = (0, .04, .08, .12, .16)
    zeroes = tuple([0] * len(uncertainty_values))
    uncertainty_types = {'Activities': (uncertainty_values, zeroes, zeroes), 'Timestamps': (zeroes, uncertainty_values, zeroes), 'Indeterminate events': (zeroes, zeroes, uncertainty_values), 'All': (uncertainty_values, uncertainty_values, uncertainty_values)}
    deviation_types = {'Activity labels': (.3, 0, 0), 'Swaps': (0, .3, 0), 'Extra events': (0, 0, .3), 'All': (.3, .3, .3)}
    net_size = 10
    nets_files = sorted(glob.glob(os.path.join('models', 'net' + str(net_size), '*.pnml')))
    model_data = [import_net(net_file) for net_file in nets_files]

    qualitative_results = defaultdict(multidict)

    for i, this_model_data in enumerate(model_data):
        net, im, fm = this_model_data
        log = apply_playout(net, im, fm, no_traces=ntraces)
        ALIGNMENTS_MEMO = {}
        for deviation_type, deviations in deviation_types.items():
            dev_a, dev_s, dev_d = deviations
            # Adding deviations
            label_set, _, dev_log = add_deviations(deepcopy(log), dev_a, dev_s, dev_d)
            for uncertainty_type, uncertainties in uncertainty_types.items():
                unc_act_values, unc_time_values, unc_indet_values = uncertainties
                qualitative_results[deviation_type][uncertainty_type][this_model_data] = []
                for j in range(len(unc_act_values)):
                    # Adding uncertainty
                    uncertain_log = deepcopy(dev_log)
                    add_uncertainty(unc_act_values[j], unc_time_values[j], unc_indet_values[j], uncertain_log, label_set=label_set)
                    print('Experiment: ' + str(i) + ', deviation = ' + str(dev_a) + ' ' + str(dev_s) + ' ' + str(dev_d) + ', uncertainty = ' + str(unc_act_values[j]) + ' ' + str(unc_time_values[j]) + ' ' + str(unc_indet_values[j]))
                    qualitative_results[deviation_type][uncertainty_type][this_model_data].append(cost_bounds_su_log(uncertain_log, net, im, fm, parameters={'ALIGNMENTS_MEMO': ALIGNMENTS_MEMO}))

    # Pickling results
    import pickle
    with open('qualitative_results_new.pickle', 'wb') as f:
        pickle.dump((uncertainty_types, qualitative_results), f, pickle.HIGHEST_PROTOCOL)

    # import pickle
    # with open('qualitative_results_new.pickle', 'rb') as f:
    #     uncertainty_types, qualitative_results = pickle.load(f)

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
    return bruteforce_time_series, improved_time_series


def quantitative_experiments():
    ntraces = 100
    uncertainty_value = .05
    uncertainty_types = {'Activities': (uncertainty_value, 0, 0), 'Timestamps': (0, uncertainty_value, 0), 'Indeterminate events': (0, 0, uncertainty_value), 'All': (uncertainty_value, uncertainty_value, uncertainty_value)}
    net_sizes = [5, 10, 15, 20]
    nets_map = {net_size: [import_net(net_file) for net_file in sorted(glob.glob(os.path.join('models', 'net' + str(net_size), '*.pnml')))] for net_size in net_sizes}

    # Nets is a dictionary where the key is an integer (the size of the net), and the value is a list of 3-uples with net, initial marking and final marking

    quantitative_results = defaultdict(dict)

    for uncertainty_type, uncertainty in uncertainty_types.items():
        unc_act_value, unc_time_value, unc_indet_value = uncertainty
        print('Testing uncertainty values: ' + str(unc_act_value) + ' ' + str(unc_time_value) + ' ' + str(unc_indet_value))
        for net_size, nets in nets_map.items():
            print('Testing net size: ' + str(net_size))
            quantitative_results[uncertainty_type][net_size] = []
            i = 0
            for net, im, fm in nets:
                print('Testing net: ' + str(i))
                log = apply_playout(net, im, fm, no_traces=ntraces)
                add_uncertainty(unc_act_value, unc_time_value, unc_indet_value, log)
                a = process_time()
                exec_alignment_lower_bound_su_log_bruteforce(log, net, im, fm)
                b = process_time()
                exec_alignment_lower_bound_su_log(log, net, im, fm)
                c = process_time()
                quantitative_results[uncertainty_type][net_size].append((b - a, c - b))
                i += 1

    # Pickling results
    import pickle
    with open('quantitative_results.pickle', 'wb') as f:
        pickle.dump((uncertainty_types, quantitative_results), f, pickle.HIGHEST_PROTOCOL)

    # import pickle
    # with open('quantitative_results.pickle', 'rb') as f:
    #     uncertainty_types, quantitative_results = pickle.load(f)

    # Plotting averages
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_mean(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b', label='Baseline')
        plots[i].plot(net_sizes, improved_time_series, '--r', label='Beh. net')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].xaxis.set_label_position('top')
        plots[i].margins(y=.15)

    plots[0].legend(loc='upper left')
    plots[0].set_ylabel('Mean time (seconds)')

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Net size (number of transitions)', ha='center', fontsize=14)

    plt.show()

    # Plotting medians
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_median(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b', label='Baseline')
        plots[i].plot(net_sizes, improved_time_series, '--r', label='Beh. net')
        plots[i].xaxis.set_label_position('top')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].margins(y=.15)

    plots[0].legend(loc='upper left')
    plots[0].set_ylabel('Median time (seconds)')

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Net size (number of transitions)', ha='center', fontsize=14)

    plt.show()

    # Plotting averages (log)
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_mean(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b', label='Baseline')
        plots[i].plot(net_sizes, improved_time_series, '--r', label='Beh. net')
        plots[i].xaxis.set_label_position('top')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].set_yscale('log')
        plots[i].margins(y=.15)

    plots[0].legend(loc='upper left')
    plots[0].set_ylabel('Mean time (seconds)')

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Net size (number of transitions)', ha='center', fontsize=14)

    plt.show()

    # Plotting medians (log)
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        bruteforce_time_series, improved_time_series = generate_data_series_quantitative_median(net_sizes, quantitative_results[uncertainty_type])
        plots[i].plot(net_sizes, bruteforce_time_series, ':b', label='Baseline')
        plots[i].plot(net_sizes, improved_time_series, '--r', label='Beh. net')
        plots[i].xaxis.set_label_position('top')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].set_yscale('log')
        plots[i].margins(y=.15)

    plots[0].legend(loc='upper left')
    plots[0].set_ylabel('Median time (seconds)')

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Net size (number of transitions)', ha='center', fontsize=14)

    plt.show()


def number_of_realizations_vs_net_size_experiment():
    ntraces = 100
    uncertainty_value = .05
    uncertainty_types = {'Activities': (uncertainty_value, 0, 0), 'Timestamps': (0, uncertainty_value, 0), 'Indeterminate events': (0, 0, uncertainty_value), 'All': (uncertainty_value, uncertainty_value, uncertainty_value)}
    net_sizes = [5, 10, 15, 20, 25, 30, 35, 40]
    nets_map = {net_size: [import_net(net_file) for net_file in sorted(glob.glob(os.path.join('models', 'net' + str(net_size), '*.pnml')))] for net_size in net_sizes}

    # Nets is a dictionary where the key is an integer (the size of the net), and the value is a list of 3-uples with net, initial marking and final marking

    number_of_realizations = defaultdict(dict)

    for uncertainty_type, uncertainty in uncertainty_types.items():
        unc_act_value, unc_time_value, unc_indet_value = uncertainty
        print('Testing uncertainty values: ' + str(unc_act_value) + ' ' + str(unc_time_value) + ' ' + str(unc_indet_value))
        for net_size, nets in nets_map.items():
            print('Testing net size: ' + str(net_size))
            number_of_realizations[uncertainty_type][net_size] = []
            i = 0
            number_of_realizations_by_log = []
            for net, im, fm in nets:
                print('Testing net: ' + str(i))
                log = apply_playout(net, im, fm, no_traces=ntraces)
                add_uncertainty(unc_act_value, unc_time_value, unc_indet_value, log)
                behavior_nets = [behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace)) for trace in log]
                number_of_realizations_by_log.append(sum([len(acyclic_net_variants_new(behavior_net, behavior_net.initial_marking, behavior_net.final_marking)) for behavior_net in behavior_nets]))
                i += 1
            number_of_realizations[uncertainty_type][net_size] = mean(number_of_realizations_by_log)

    # Pickling results
    import pickle
    with open('number_of_realizations_vs_net_size.pickle', 'wb') as f:
        pickle.dump((uncertainty_types, number_of_realizations), f, pickle.HIGHEST_PROTOCOL)

    # import pickle
    # with open('number_of_realizations_vs_net_size.pickle', 'rb') as f:
    #     uncertainty_types, number_of_realizations = pickle.load(f)

    # Plotting averages and medians (log)
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        mean_series = [number_of_realizations[uncertainty_type][net_size] for net_size in net_sizes]
        plots[i].plot(net_sizes, mean_series, 'r')
        plots[i].xaxis.set_label_position('top')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].set_yscale('log')
        plots[i].margins(y=.15)

    plots[0].set_ylabel('Number of realizations')

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Net size (number of transitions)', ha='center', fontsize=14)

    plt.show()


def number_of_realizations_vs_uncertainty_experiment():
    ntraces = 100
    uncertainty_values = (0, .02, .04, .06, .08, .1, .12, .14)
    zeroes = tuple([0] * len(uncertainty_values))
    uncertainty_types = {'Activities': (uncertainty_values, zeroes, zeroes), 'Timestamps': (zeroes, uncertainty_values, zeroes), 'Indeterminate events': (zeroes, zeroes, uncertainty_values), 'All': (uncertainty_values, uncertainty_values, uncertainty_values)}
    net_size = 10
    nets_files = sorted(glob.glob(os.path.join('models', 'net' + str(net_size), '*.pnml')))
    model_data = [import_net(net_file) for net_file in nets_files]

    number_of_realizations = dict()

    for uncertainty_type, uncertainties in uncertainty_types.items():
        unc_act_values, unc_time_values, unc_indet_values = uncertainties
        number_of_realizations[uncertainty_type] = []
        for j in range(len(unc_act_values)):
            number_of_realizations_by_log = []
            for this_model_data in model_data:
                net, im, fm = this_model_data
                log = apply_playout(net, im, fm, no_traces=ntraces)
                # Adding uncertainty
                uncertain_log = deepcopy(log)
                add_uncertainty(unc_act_values[j], unc_time_values[j], unc_indet_values[j], uncertain_log)
                behavior_nets = [behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace)) for trace in uncertain_log]
                number_of_realizations_by_log.append(sum([len(acyclic_net_variants_new(behavior_net, behavior_net.initial_marking, behavior_net.final_marking)) for behavior_net in behavior_nets]))
            number_of_realizations[uncertainty_type].append(mean(number_of_realizations_by_log))

    # Pickling results
    import pickle
    with open('number_of_realizations_vs_uncertainty.pickle', 'wb') as f:
        pickle.dump((uncertainty_types, number_of_realizations), f, pickle.HIGHEST_PROTOCOL)

    # import pickle
    # with open('number_of_realizations_vs_uncertainty.pickle', 'rb') as f:
    #     uncertainty_types, number_of_realizations = pickle.load(f)

    # Plotting averages and medians (log)
    fig, plots = plt.subplots(ncols=len(uncertainty_types), sharey='row', gridspec_kw={'hspace': 0, 'wspace': 0})
    for i, uncertainty_type in enumerate(uncertainty_types):
        plots[i].plot(uncertainty_values, number_of_realizations[uncertainty_type], 'r')
        plots[i].xaxis.set_label_position('top')
        plots[i].set_xlabel(uncertainty_type)
        plots[i].set_yscale('log')
        plots[i].margins(y=.15)

    plots[0].set_ylabel('Number of realizations')

    for diagram in plots.flat:
        diagram.label_outer()

    fig.text(0.525, 0.01, 'Uncertainty (percentage)', ha='center', fontsize=14)

    plt.show()


if __name__ == '__main__':
    qualitative_experiments()
    quantitative_experiments()
    number_of_realizations_vs_net_size_experiment()
    number_of_realizations_vs_uncertainty_experiment()
