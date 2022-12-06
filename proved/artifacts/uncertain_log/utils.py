from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net as behavior_net_builder
from proved.artifacts.behavior_net.utils import acyclic_net_variants


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

    return acyclic_net_variants(behavior_net, bn_i, bn_f)


def random_realization(trace):
    """
    Returns one random realization of an uncertain trace. Samples with indicated distribution in case of weak uncertainty, and with uniform distribution in case of strong uncertainty.

    :param trace: An uncertain trace.
    :type trace:
    :return: One random realization of the trace in input.
    :rtype:
    """
