from copy import deepcopy
import random
from datetime import datetime
import importlib

from pm4py.objects.log.log import Trace
from pm4py.objects.log.util import sorting
from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY
import numpy as np

from proved.artifacts.behavior_graph import behavior_graph
from proved.artifacts.behavior_net import behavior_net as behavior_net_builder
from proved.artifacts.behavior_net.utils import acyclic_net_variants
from proved.xes_keys import DEFAULT_U_DISCRETE_STRONG, DEFAULT_U_CONTINUOUS_STRONG, DEFAULT_U_DISCRETE_WEAK, DEFAULT_U_CONTINUOUS_WEAK, DEFAULT_U_TIMESTAMP_MIN_KEY, DEFAULT_U_TIMESTAMP_MAX_KEY, DEFAULT_U_PROBABILITY_KEY, DEFAULT_U_DENSITY_FUNCTION_KEY, DEFAULT_U_FUNCTION_PARAMETERS_KEY, DEFAULT_U_NAME_KEY, DEFAULT_U_TIMESTAMP_KEY, DEFAULT_U_INDETERMINACY_KEY


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


def random_realization(trace, activity_key=DEFAULT_NAME_KEY, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_discrete_strong=DEFAULT_U_DISCRETE_STRONG, u_continuous_strong=DEFAULT_U_CONTINUOUS_STRONG, u_discrete_weak=DEFAULT_U_DISCRETE_WEAK, u_continuous_weak=DEFAULT_U_CONTINUOUS_WEAK, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY, u_probability_key=DEFAULT_U_PROBABILITY_KEY, u_function_key=DEFAULT_U_DENSITY_FUNCTION_KEY, u_params_key=DEFAULT_U_FUNCTION_PARAMETERS_KEY, u_activity_key=DEFAULT_U_NAME_KEY, u_timestamp_key=DEFAULT_U_TIMESTAMP_KEY, u_indeterminacy_key=DEFAULT_U_INDETERMINACY_KEY):
    """
    Returns one random realization of an uncertain trace. Samples with indicated distribution in case of weak uncertainty, and with uniform distribution in case of strong uncertainty.

    :param trace: An uncertain trace.
    :type trace:
    :return: One random realization of the trace in input.
    :rtype: trace
    """

    realization = Trace()
    for uncertain_event in trace:
        p = 1
        if u_indeterminacy_key in uncertain_event and uncertain_event[u_indeterminacy_key]['value'] == u_discrete_strong:
            p = .5
        elif u_indeterminacy_key in uncertain_event and uncertain_event[u_indeterminacy_key]['value'] == u_discrete_weak:
            p = uncertain_event[u_indeterminacy_key][u_probability_key]
        if random.random() < p:
            event = deepcopy(uncertain_event)
            if u_activity_key in uncertain_event and uncertain_event[u_activity_key]['value'] == u_discrete_strong:
                event[activity_key] = np.random.choice(list(uncertain_event[u_activity_key]['children'].keys()))
            elif u_activity_key in uncertain_event and uncertain_event[u_activity_key]['value'] == u_discrete_weak:
                event[activity_key] = np.random.choice(list(uncertain_event[u_activity_key]['children'].keys()), p=list(uncertain_event[u_activity_key]['children'].values()))
            if u_timestamp_key in uncertain_event and uncertain_event[u_timestamp_key]['value'] == u_continuous_strong:
                # WARNING: this operates with a resolution of seconds. It may be improved to microseconds with a more complex operation
                event[timestamp_key] = datetime.fromtimestamp(random.randint(uncertain_event[u_timestamp_key]['children'][u_timestamp_min_key].timestamp, uncertain_event[u_timestamp_key]['children'][u_timestamp_max_key].timestamp), uncertain_event[u_timestamp_key]['children'][u_timestamp_min_key].tzinfo)
            elif u_timestamp_key in uncertain_event and uncertain_event[u_timestamp_key]['value'] == u_continuous_weak:
                module_name, class_name = uncertain_event[u_timestamp_key]['children'][u_function_key]['value'].rsplit('.', 1)
                event[timestamp_key] = getattr(importlib.import_module(module_name), class_name)(**dict(uncertain_event[u_timestamp_key]['children'][u_function_key]['children']))
            realization.append(deepcopy(event))
    return sorting.sort_timestamp_trace(realization)
