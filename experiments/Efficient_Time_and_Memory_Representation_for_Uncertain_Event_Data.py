import datetime
import glob
import os
import time
from collections import defaultdict
from datetime import timedelta
from time import process_time

import matplotlib.pyplot as plt
from matplotlib import rc, ticker
rc('text', usetex=True)
from pm4py.objects.log.importer.xes import factory as xes_import_factory
from pm4py.objects.log.log import Trace, Event
from pympler import asizeof

from proved.algorithms.conformance.alignments.alignment_bounds_su import alignment_lower_bound_su_trace
from proved.artifacts.behavior_net import behavior_net
from proved.artifacts.behavior_graph import tr_behavior_graph
from proved.artifacts.uncertain_log import uncertain_log
from proved.simulation.bewilderer.add_timestamps import add_uncertain_timestamp_to_log
from proved.simulation.bewilderer.add_uncertainty import add_uncertainty

from experiments.utils import import_net, apply_playout


def create_log(num_traces, len_traces, p_u_time):
    """
    Creates an event log with fixed-length traces, and all events have activity label 'a'.
    Timestamps are uncertain with some probability.
    :param num_traces: number of traces to be generated
    :param len_traces: length of the traces in the log
    :param p_u_time: probability of uncertain timestamp
    :return: an event log with uncertain timestamps
    """

    base_time = datetime.datetime.fromtimestamp(10000000)
    log = []
    for i in range(num_traces):
        t = Trace()
        for j in range(len_traces):
            t.append(Event({'concept:name': str(j), 'time:timestamp': base_time + timedelta(hours=j)}))
        log.append(t)

    add_uncertain_timestamp_to_log(p_u_time, log)
    return log


def generate_data_series(net_sizes, experiment_results):
    transitive_reduction_time_series = [0] * len(net_sizes)
    multiset_improved_time_series = [0] * len(net_sizes)
    for i, net_size in enumerate(net_sizes):
        for one_net_run_time in experiment_results[net_size]:
            transitive_reduction_time_series[i] += one_net_run_time[0]
            multiset_improved_time_series[i] += one_net_run_time[1]
    return [series_value / len(experiment_results[net_sizes[0]]) for series_value in transitive_reduction_time_series], [series_value / len(experiment_results[net_sizes[0]]) for series_value in multiset_improved_time_series]


### EXPERIMENT PARAMS
# Common parameters
TR_LEGEND_LABEL = 'TrRed'
IMP_LEGEND_LABEL = 'Imp'
MULT_IMP_LEGEND_LABEL = 'Improved'
TR_PLOT_STYLE = '-b'
MULT_IMP_PLOT_STYLE = '--r'
BPI_2012_PATH = os.path.join('BPI_Challenge_2012.xes')
HELPDESK_PATH = os.path.join('Help_Desk_event_log.xes')
ROAD_TRAFFIC_PATH = os.path.join('Road_Traffic_Fine_Management_Process.xes')
BPI_2012_LABEL = 'BPIC 2012'
HELPDESK_LABEL = 'HelpDesk'
ROAD_TRAFFIC_LABEL = 'RTFM'

# Experiment 1: Computing time against log size
T1_N_TRACES = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
T1_TRACE_LENGTH = 20
T1_UNCERTAINTY = .5

# Experiment 2: Computing time against trace length
T2_N_TRACES = 100
T2_TRACE_LENGTH = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]
T2_UNCERTAINTY = .5

# Experiment 3: Computing time against uncertainty percentage
T3_N_TRACES = 100
T3_TRACE_LENGTH = 100
T3_UNCERTAINTY = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]

# Experiment 4: Memory occupation against log size
T4_N_TRACES = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000]
T4_TRACE_LENGTH = 10
T4_UNCERTAINTY = .5

# Experiment 5: Computing time against uncertainty percentage (real life)
T5_UNCERTAINTY = [0, .1, .2, .3, .4, .5]

# Experiment 6: Conformance checking computing time against model size
T6_N_TRACES = 500
T6_NET_SIZES = [5, 10, 15, 20, 25, 30, 35, 40]
T6_UNCERTAINTY = .1


def e1_log_size_vs_time():
    # Experiment 1: Computing time against log size
    transitive_reduction_times = []
    improved_times = []
    multiset_improved_times = []
    for n_traces in T1_N_TRACES:
        log = create_log(n_traces, T1_TRACE_LENGTH, T1_UNCERTAINTY)
        a = process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        transitive_reduction_times.append(process_time() - a)
        a = process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        multiset_improved_times.append(process_time() - a)

    # Pickling results
    import pickle
    with open('exp1.pickle', 'wb') as f:
        pickle.dump((T1_N_TRACES, (transitive_reduction_times, improved_times, multiset_improved_times)), f, pickle.HIGHEST_PROTOCOL)

    # # Loading results
    # import pickle
    # with open('exp1.pickle', 'rb') as f:
    #     (T1_N_TRACES, (transitive_reduction_times, improved_times, multiset_improved_times)) = pickle.load(f)

    # Plotting
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(T1_N_TRACES, transitive_reduction_times, TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    ax.plot(T1_N_TRACES, multiset_improved_times, MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    # Labels with relative values
    for k, point in enumerate(multiset_improved_times):
        ax.annotate(str(round(point / transitive_reduction_times[k] * 100, 2)) + '\%', xy=(T1_N_TRACES[k], multiset_improved_times[k]), xytext=(-10, 10), textcoords='offset pixels', annotation_clip=False, size=8)
    ax.get_xaxis().set_major_formatter(
        ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    ax.set_xlabel('Log size (number of traces)')
    ax.set_ylabel('Behavior graph building time (seconds)')
    ax.legend(frameon=False)

    plt.show()
    plt.clf()


def e2_trace_length_vs_time():
    # Experiment 2: Computing time against trace length
    transitive_reduction_times = []
    improved_times = []
    multiset_improved_times = []
    for length in T2_TRACE_LENGTH:
        print('Running length: ' + str(length))
        log = create_log(T2_N_TRACES, length, T2_UNCERTAINTY)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        transitive_reduction_times.append(time.process_time() - a)
        a = process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        multiset_improved_times.append(process_time() - a)

    # Pickling results
    import pickle
    with open('exp2.pickle', 'wb') as f:
        pickle.dump((T2_TRACE_LENGTH, (transitive_reduction_times, improved_times, multiset_improved_times)), f, pickle.HIGHEST_PROTOCOL)

    # # Loading results
    # import pickle
    # with open('exp2.pickle', 'rb') as f:
    #     (T2_TRACE_LENGTH, (transitive_reduction_times, improved_times, multiset_improved_times)) = pickle.load(f)

    # Plotting
    fig = plt.figure()
    ax = plt.axes()
    ax.set_yscale('log')
    ax.plot(T2_TRACE_LENGTH, transitive_reduction_times, TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    ax.plot(T2_TRACE_LENGTH, multiset_improved_times, MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    # Labels with relative values
    for k, point in enumerate(multiset_improved_times):
        ax.annotate(str(round(point / transitive_reduction_times[k] * 100, 2)) + '\%', xy=(T2_TRACE_LENGTH[k], multiset_improved_times[k]), xytext=(-10, 10), textcoords='offset pixels', annotation_clip=False, size=10)
    ax.set_xlabel('Trace length (number of events)')
    ax.set_ylabel('Behavior graph building time (seconds)')
    ax.legend(frameon=False)

    plt.show()
    plt.clf()


def e3_prob_uncertainty_vs_time():
    # Experiment 3: Computing time against uncertainty percentage
    transitive_reduction_times = []
    improved_times = []
    multiset_improved_times = []
    for p_u_time in T3_UNCERTAINTY:
        log = create_log(T3_N_TRACES, T3_TRACE_LENGTH, p_u_time)
        a = process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        transitive_reduction_times.append(process_time() - a)
        a = process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        multiset_improved_times.append(process_time() - a)

    # Pickling results
    import pickle
    with open('exp3.pickle', 'wb') as f:
        pickle.dump((T3_UNCERTAINTY, (transitive_reduction_times, improved_times, multiset_improved_times)), f, pickle.HIGHEST_PROTOCOL)

    # # Loading results
    # import pickle
    # with open('exp3.pickle', 'rb') as f:
    #     (T3_UNCERTAINTY, (transitive_reduction_times, improved_times, multiset_improved_times)) = pickle.load(f)

    # Plotting
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(T3_UNCERTAINTY, transitive_reduction_times, TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    ax.plot(T3_UNCERTAINTY, multiset_improved_times, MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    # Labels with relative values
    for k, point in enumerate(multiset_improved_times):
        ax.annotate(str(round(point / transitive_reduction_times[k] * 100, 2)) + '\%', xy=(T3_UNCERTAINTY[k], multiset_improved_times[k]), xytext=(-5, 10), textcoords='offset pixels', annotation_clip=False, size=8)
    ax.set_xlabel('Uncertainty (\%)')
    ax.set_ylabel('Behavior graph building time (seconds)')
    ax.legend(frameon=False)

    plt.show()
    plt.clf()


def e4_log_size_vs_memory():
    # Experiment 4: Memory occupation against log size
    transitive_reduction_memory = []
    improved_memory = []
    multiset_improved_memory = []
    for n_traces in T4_N_TRACES:
        print('Running n traces: ' + str(n_traces))
        log = create_log(n_traces, T4_TRACE_LENGTH, T4_UNCERTAINTY)
        transitive_reduction_memory.append(asizeof.asizeof([tr_behavior_graph.TRBehaviorGraph(trace) for trace in log]))
        uncertain_log_object = uncertain_log.UncertainLog(log)
        multiset_improved_memory.append(asizeof.asizeof([variant[0] for variant in uncertain_log_object.behavior_graphs_map.values()]))

    # Pickling results
    import pickle
    with open('exp4.pickle', 'wb') as f:
        pickle.dump((T4_N_TRACES, (transitive_reduction_memory, improved_memory, multiset_improved_memory)), f, pickle.HIGHEST_PROTOCOL)

    # # Loading results
    # import pickle
    # with open('exp4.pickle', 'rb') as f:
    #     (T4_N_TRACES, (transitive_reduction_memory, improved_memory, multiset_improved_memory)) = pickle.load(f)

    # Plotting
    fig = plt.figure()
    ax = plt.axes()
    ax.plot(T4_N_TRACES, transitive_reduction_memory, TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    ax.plot(T4_N_TRACES, multiset_improved_memory, MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    # Labels with relative values
    for k, point in enumerate(multiset_improved_memory):
        if k == 0:
            ax.annotate(str(round(point / transitive_reduction_memory[k] * 100, 2)) + '\%', xy=(T4_N_TRACES[k], multiset_improved_memory[k]), xytext=(-10, -5), textcoords='offset pixels', annotation_clip=False, size=8)
        else:
            ax.annotate(str(round(point / transitive_reduction_memory[k] * 100, 2)) + '\%', xy=(T4_N_TRACES[k], multiset_improved_memory[k]), xytext=(-10, -15), textcoords='offset pixels', annotation_clip=False, size=8)
    ax.get_xaxis().set_major_formatter(
        ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    ax.set_xlabel('Log size (number of traces)')
    ax.set_ylabel('Memory occupation (bytes)')
    ax.legend(frameon=False)

    plt.show()
    plt.clf()


def e5_perc_uncertainty_vs_time_rl():
    # Experiment 5: Computing time against uncertainty percentage (real life)
    bpi_transitive_reduction_times = []
    bpi_improved_times = []
    bpi_multiset_improved_times = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(BPI_2012_PATH)
        add_uncertain_timestamp_to_log(p_u_time, log)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        bpi_transitive_reduction_times.append(process_time() - a)
        a = time.process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        bpi_multiset_improved_times.append(process_time() - a)

    hd_transitive_reduction_times = []
    hd_improved_times = []
    hd_multiset_improved_times = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(HELPDESK_PATH)
        add_uncertain_timestamp_to_log(p_u_time, log)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        hd_transitive_reduction_times.append(process_time() - a)
        a = time.process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        hd_multiset_improved_times.append(process_time() - a)

    rtfm_transitive_reduction_times = []
    rtfm_improved_times = []
    rtfm_multiset_improved_times = []
    for p_u_time in T5_UNCERTAINTY:
        log = xes_import_factory.apply(ROAD_TRAFFIC_PATH)
        add_uncertain_timestamp_to_log(p_u_time, log)
        a = time.process_time()
        for trace in log:
            bg = tr_behavior_graph.TRBehaviorGraph(trace)
        rtfm_transitive_reduction_times.append(process_time() - a)
        a = time.process_time()
        uncertain_log_object = uncertain_log.UncertainLog(log)
        rtfm_multiset_improved_times.append(process_time() - a)

    # Pickling results
    import pickle
    with open('exp5.pickle', 'wb') as f:
        pickle.dump((T5_UNCERTAINTY, (bpi_transitive_reduction_times, bpi_improved_times, bpi_multiset_improved_times), (hd_transitive_reduction_times, hd_improved_times, hd_multiset_improved_times), (rtfm_transitive_reduction_times, rtfm_improved_times, rtfm_multiset_improved_times)), f, pickle.HIGHEST_PROTOCOL)

    # # Loading results
    # import pickle
    # with open('exp5.pickle', 'rb') as f:
    #     (T5_UNCERTAINTY, (bpi_transitive_reduction_times, bpi_improved_times, bpi_multiset_improved_times), (hd_transitive_reduction_times, hd_improved_times, hd_multiset_improved_times), (rtfm_transitive_reduction_times, rtfm_improved_times, rtfm_multiset_improved_times)) = pickle.load(f)

    # Plotting
    fig, plots = plt.subplots(ncols=3)
    plots[0].set_ylabel('Behavior graph building time (seconds)')
    plots[0].title.set_text(BPI_2012_LABEL)
    plots[1].title.set_text(HELPDESK_LABEL)
    plots[2].title.set_text(ROAD_TRAFFIC_LABEL)
    plots[0].set_xlabel('Uncertainty (\%)')
    plots[1].set_xlabel('Uncertainty (\%)')
    plots[2].set_xlabel('Uncertainty (\%)')
    plots[0].plot(T5_UNCERTAINTY, bpi_transitive_reduction_times, TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[0].plot(T5_UNCERTAINTY, bpi_multiset_improved_times, MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    # for k, point in enumerate(bpi_multiset_improved_times):
    #     plots[0].annotate(str(round(point / bpi_transitive_reduction_times[k] * 100, 2)) + '\%', xy=(T5_UNCERTAINTY[k], bpi_multiset_improved_times[k]), xytext=(-10, -15), textcoords='offset pixels', annotation_clip=False, size=6)
    plots[1].margins(y=.15)
    plots[1].plot(T5_UNCERTAINTY, hd_transitive_reduction_times, TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[1].plot(T5_UNCERTAINTY, hd_multiset_improved_times, MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    # for k, point in enumerate(hd_multiset_improved_times):
    #     plots[1].annotate(str(round(point / hd_transitive_reduction_times[k] * 100, 2)) + '\%', xy=(T5_UNCERTAINTY[k], hd_multiset_improved_times[k]), xytext=(-10, -15), textcoords='offset pixels', annotation_clip=False, size=6)
    # plots[2].margins(y=.15)
    plots[2].plot(T5_UNCERTAINTY, rtfm_transitive_reduction_times, TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    plots[2].plot(T5_UNCERTAINTY, rtfm_multiset_improved_times, MULT_IMP_PLOT_STYLE, label=MULT_IMP_LEGEND_LABEL)
    # for k, point in enumerate(rtfm_multiset_improved_times):
    #     plots[2].annotate(str(round(point / rtfm_transitive_reduction_times[k] * 100, 2)) + '\%', xy=(T5_UNCERTAINTY[k], rtfm_multiset_improved_times[k]), xytext=(-10, -15), textcoords='offset pixels', annotation_clip=False, size=6)

    fig.tight_layout()

    plt.show()
    plt.clf()


def e6_model_size_vs_conformance_checking_time():
    # Experiment 6: Conformance checking computing time against model size
    uncertainty_types = {'Activities': (T6_UNCERTAINTY, 0, 0), 'Timestamps': (0, T6_UNCERTAINTY, 0), 'Indeterminate events': (0, 0, T6_UNCERTAINTY), 'All': (T6_UNCERTAINTY, T6_UNCERTAINTY, T6_UNCERTAINTY)}
    nets_map = {net_size: [import_net(net_file) for net_file in sorted(glob.glob(os.path.join('models', 'net' + str(net_size), '*.pnml')))] for net_size in T6_NET_SIZES}

    conformance_checking_results = defaultdict(dict)

    for uncertainty_type, uncertainty in uncertainty_types.items():
        print('Running uncertainty type: ' + str(uncertainty_type))
        unc_act_value, unc_time_value, unc_indet_value = uncertainty
        for net_size, nets in nets_map.items():
            print('Running net size: ' + str(net_size))
            conformance_checking_results[uncertainty_type][net_size] = []
            for i, (net, im, fm) in enumerate(nets):
                print('Running net: ' + str(i))
                log = apply_playout(net, im, fm, no_traces=T6_N_TRACES)
                add_uncertainty(unc_act_value, unc_time_value, unc_indet_value, log)
                a = process_time()
                for trace in log:
                    bg = tr_behavior_graph.TRBehaviorGraph(trace)
                    bn = behavior_net.BehaviorNet(bg)
                    alignment_lower_bound_su_trace(bn, bn.initial_marking, bn.final_marking, net, im, fm)
                b = process_time()
                uncertain_log_object = uncertain_log.UncertainLog(log)
                for bg, _ in uncertain_log_object.behavior_graphs_map.values():
                    bn = behavior_net.BehaviorNet(bg)
                    alignment_lower_bound_su_trace(bn, bn.initial_marking, bn.final_marking, net, im, fm)
                c = process_time()
                conformance_checking_results[uncertainty_type][net_size].append((b - a, c - b))

    # Pickling results
    import pickle
    with open('exp6.pickle', 'wb') as f:
        pickle.dump((T6_UNCERTAINTY, uncertainty_types, conformance_checking_results), f, pickle.HIGHEST_PROTOCOL)

    # # Loading results
    # import pickle
    # with open('exp6.pickle', 'rb') as f:
    #     T6_UNCERTAINTY, conformance_checking_results = pickle.load(f)

    # Plotting averages
    fig, plots = plt.subplots(ncols=2, nrows=2)
    transitive_reduction_time_series, multiset_improved_time_series = generate_data_series(T6_NET_SIZES, conformance_checking_results['Activities'])
    plots[0][0].plot(T6_NET_SIZES, [point / transitive_reduction_time_series[k] * 100 for k, point in enumerate(multiset_improved_time_series)], TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    for k, point in enumerate(multiset_improved_time_series):
        if k == 0:
            plots[0][0].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, 10), textcoords='offset pixels', annotation_clip=False, size=6)
        else:
            plots[0][0].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, -15), textcoords='offset pixels', annotation_clip=False, size=6)
    plots[0][0].title.set_text('Activities')
    plots[0][0].set_xlabel('Number of transitions')
    plots[0][0].set_ylabel('Time variation (\%)')

    transitive_reduction_time_series, multiset_improved_time_series = generate_data_series(T6_NET_SIZES, conformance_checking_results['Timestamps'])
    plots[0][1].plot(T6_NET_SIZES, [point / transitive_reduction_time_series[k] * 100 for k, point in enumerate(multiset_improved_time_series)], TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    for k, point in enumerate(multiset_improved_time_series):
        if k == 0:
            plots[0][1].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, 10), textcoords='offset pixels', annotation_clip=False, size=6)
        else:
            plots[0][1].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, -15), textcoords='offset pixels', annotation_clip=False, size=6)
    plots[0][1].title.set_text('Timestamps')
    plots[0][1].set_xlabel('Number of transitions')
    plots[0][1].set_ylabel('Time variation (\%)')

    transitive_reduction_time_series, multiset_improved_time_series = generate_data_series(T6_NET_SIZES, conformance_checking_results['Indeterminate events'])
    plots[1][0].plot(T6_NET_SIZES, [point / transitive_reduction_time_series[k] * 100 for k, point in enumerate(multiset_improved_time_series)], TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    for k, point in enumerate(multiset_improved_time_series):
        if k == 0:
            plots[1][0].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, 10), textcoords='offset pixels', annotation_clip=False, size=6)
        else:
            plots[1][0].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, -15), textcoords='offset pixels', annotation_clip=False, size=6)
    plots[1][0].title.set_text('Indeterminate events')
    plots[1][0].set_xlabel('Number of transitions')
    plots[1][0].set_ylabel('Time variation (\%)')

    transitive_reduction_time_series, multiset_improved_time_series = generate_data_series(T6_NET_SIZES, conformance_checking_results['All'])
    plots[1][1].plot(T6_NET_SIZES, [point / transitive_reduction_time_series[k] * 100 for k, point in enumerate(multiset_improved_time_series)], TR_PLOT_STYLE, label=TR_LEGEND_LABEL)
    for k, point in enumerate(multiset_improved_time_series):
        if k == 0:
            plots[1][1].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, 10), textcoords='offset pixels', annotation_clip=False, size=6)
        else:
            plots[1][1].annotate(str(round(point / transitive_reduction_time_series[k] * 100, 2)) + '\%', xy=(T6_NET_SIZES[k], point / transitive_reduction_time_series[k] * 100), xytext=(-5, -15), textcoords='offset pixels', annotation_clip=False, size=6)
    plots[1][1].title.set_text('All')
    plots[1][1].set_xlabel('Number of transitions')
    plots[1][1].set_ylabel('Time variation (\%)')

    fig.tight_layout()

    plt.show()
    plt.clf()


if __name__ == '__main__':
    e1_log_size_vs_time()
    e2_trace_length_vs_time()
    e3_prob_uncertainty_vs_time()
    e4_log_size_vs_memory()
    e6_model_size_vs_conformance_checking_time()
    e5_perc_uncertainty_vs_time_rl()
