import random
import time
import csv
from datetime import datetime
from datetime import timedelta

from pm4py.objects.log.log import Trace, Event

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


fixed_prob = .4
fixed_ntraces = 1000
fixed_length = 10


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


if __name__ == '__main__':
    probs = [0, .1, .2, .3, .4, .5, .6]
    nstraces = [500, 1000, 1500, 2000, 2500]
    lengths = [10, 15, 20, 25, 30]

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
