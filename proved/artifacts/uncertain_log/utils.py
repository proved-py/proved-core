from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net as behavior_net_builder
from proved.artifacts.behavior_net.utils import generate_all_traces, generate_all_sequences


def realization_set(trace):
    """
    Returns the realization set of an uncertain trace.

    :param trace: An uncertain trace.
    :type trace:
    :return: The realization set of the trace in input.
    :rtype:
    """

    behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))
    bn_i = behavior_net.initial_marking
    bn_f = behavior_net.final_marking

    return generate_all_traces(behavior_net, bn_i, bn_f)


def realization_set_sequences(trace):
    """
    Returns the realization set of an uncertain trace in the form of lists of strings.

    :param trace: An uncertain trace.
    :type trace:
    :return: The realization set of the trace in input.
    :rtype:
    """

    behavior_net = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))
    bn_i = behavior_net.initial_marking
    bn_f = behavior_net.final_marking

    return generate_all_sequences(behavior_net, bn_i, bn_f)
