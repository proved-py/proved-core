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

    behavior_net, bn_i, bn_f = behavior_net_builder.BehaviorNet(behavior_graph.BehaviorGraph(trace))
    return acyclic_net_variants(behavior_net, bn_i, bn_f)
