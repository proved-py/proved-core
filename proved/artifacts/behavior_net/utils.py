from pm4py.objects import petri
from pm4py.objects.log.log import Trace, Event
from pm4py.util.xes_constants import DEFAULT_NAME_KEY


def acyclic_net_variants(net, initial_marking, final_marking, activity_key=DEFAULT_NAME_KEY):
    """
    Given an acyclic accepting Petri net, initial and final marking extracts a set of variants (in form of traces)
    replayable on the net.
    Warning: this function is based on a marking exploration. If the accepting Petri net contains loops, the method
    will not work properly as it stops the search if a specific marking has already been encountered.

    Parameters
    ----------
    :param net: An acyclic workflow net
    :param initial_marking: The initial marking of the net.
    :param final_marking: The final marking of the net.

    Returns
    -------
    :return: variants: :class:`list` Set of variants - in the form of Trace objects - obtainable executing the net

    """
    active = {(initial_marking, ())}
    visited = set()
    variants = set()
    hash_final_marking = hash(final_marking)
    while active:
        curr_marking, curr_partial_trace = active.pop()
        hash_curr_pair = hash((curr_marking, curr_partial_trace))
        enabled_transitions = petri.semantics.enabled_transitions(net, curr_marking)
        for transition in enabled_transitions:
            if transition.label is not None:
                next_partial_trace = curr_partial_trace + (repr(transition),)
            else:
                next_partial_trace = curr_partial_trace
            next_marking = petri.semantics.execute(transition, net, curr_marking)
            hash_next_pair = hash((next_marking, next_partial_trace))

            if hash(next_marking) == hash_final_marking:
                variants.add(next_partial_trace)
            else:
                # If the next marking hash is not in visited, if the next marking+partial trace is different from the current one+partial trace
                if hash_next_pair not in visited and hash_curr_pair != hash_next_pair:
                    active.add((next_marking, next_partial_trace))
        visited.add(hash_curr_pair)
    trace_variants = []
    for variant in variants:
        trace = Trace()
        for activity_label in variant:
            trace.append(Event({activity_key: activity_label}))
        trace_variants.append(trace)
    return trace_variants
