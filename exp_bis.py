import random
import time
import csv
from datetime import datetime
from datetime import timedelta

from pm4py.objects.log.log import Trace, Event
from pm4py.objects.log.importer.xes import factory as xes_import_factory

from proved.artifacts.behavior_graph import behavior_graph


def create_log(numtraces, lentraces, p_u_time):
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


def introduce_uncertainty(log, p_u_time):
    timevariation = timedelta(seconds=1)
    for trace in log:
        if len(trace) > 1:
            for i, event in enumerate(trace):
                if random.random() < p_u_time:
                    if i == 0:
                        event["u:time:timestamp_left"] = event['time:timestamp']
                        event["u:time:timestamp_right"] = trace[i + 1]['time:timestamp'] + timevariation
                    elif i == len(trace) - 1:
                        event["u:time:timestamp_left"] = trace[i - 1]['time:timestamp'] - timevariation
                        event["u:time:timestamp_right"] = event['time:timestamp']
                    else:
                        event["u:time:timestamp_left"] = trace[i - 1]['time:timestamp'] - timevariation
                        event["u:time:timestamp_right"] = trace[i + 1]['time:timestamp'] + timevariation


fixed_prob = .4
fixed_ntraces = 1000
fixed_length = 50


def probability_experiment(probs):
    naive_times = []
    improved_times = []
    for p_u_time in probs:
        log = create_log(fixed_ntraces, fixed_length, p_u_time)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.TRBehaviorGraph(trace)
        naive_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)

    return naive_times, improved_times


def ntraces_experiment(nstraces):
    naive_times = []
    improved_times = []
    for n in nstraces:
        log = create_log(n, fixed_length, fixed_prob)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.TRBehaviorGraph(trace)
        naive_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)

    return naive_times, improved_times


def length_experiment(lengths):
    naive_times = []
    improved_times = []
    for length in lengths:
        log = create_log(fixed_ntraces, length, fixed_prob)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.TRBehaviorGraph(trace)
        naive_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)

    return naive_times, improved_times


def reallife_experiments(logfile, probs):
    naive_times = []
    improved_times = []
    for p_u_time in probs:
        log = xes_import_factory.apply(logfile)
        introduce_uncertainty(log, p_u_time)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.TRBehaviorGraph(trace)
        naive_times.append(time.process_time() - a)
        a = time.process_time()
        for trace in log:
            bg = behavior_graph.BehaviorGraph(trace)
        improved_times.append(time.process_time() - a)

    return naive_times, improved_times


if __name__ == '__main__':
    probs = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1]
    nstraces = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500,
                9000, 9500, 10000]
    # lengths = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    # lengths = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300]
    lengths = [100, 150, 200, 250, 300, 350, 400, 450, 500]
    reallife_probs = [0, .4, .8]
    reallife_logs = ['', '', '']

    random.seed(123456)

    ntests = 10

    # probs_results = [probability_experiment(probs) for i in range(ntests)]
    # with open('probs_results_naive.csv', 'w') as csvfile:
    #     csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
    #     csvwriter.writerow(probs)
    #     for line in probs_results:
    #         csvwriter.writerow(line[0])
    # with open('probs_results_improved.csv', 'w') as csvfile:
    #     csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
    #     csvwriter.writerow(probs)
    #     for line in probs_results:
    #         csvwriter.writerow(line[1])
    #
    # ntraces_results = [ntraces_experiment(nstraces) for i in range(ntests)]
    # with open('ntraces_results_naive.csv', 'w') as csvfile:
    #     csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
    #     csvwriter.writerow(nstraces)
    #     for line in ntraces_results:
    #         csvwriter.writerow(line[0])
    # with open('ntraces_results_improved.csv', 'w') as csvfile:
    #     csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
    #     csvwriter.writerow(nstraces)
    #     for line in ntraces_results:
    #         csvwriter.writerow(line[1])

    ############################################################################
    ############################################################################
    ############################################################################
    # length_results = [length_experiment(lengths) for i in range(ntests)]
    # with open('lengths_results_naive.csv', 'w') as csvfile:
    #     csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
    #     csvwriter.writerow(lengths)
    #     for line in length_results:
    #         csvwriter.writerow(line[0])
    # with open('lengths_results_improved.csv', 'w') as csvfile:
    #     csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
    #     csvwriter.writerow(lengths)
    #     for line in length_results:
    #         csvwriter.writerow(line[1])
    #
    for logfile in reallife_logs:
        reallife_results = [reallife_experiments(logfile, reallife_probs) for i in range(ntests)]
        with open(logfile + '_results_naive.csv', 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
            csvwriter.writerow(reallife_probs)
            for line in reallife_results:
                csvwriter.writerow(line[0])
        with open(logfile + '_results_improved.csv', 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"')
            csvwriter.writerow(reallife_probs)
            for line in reallife_results:
                csvwriter.writerow(line[1])

