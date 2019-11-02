from pm4py.objects.transition_system import utils
from pm4py.objects.log.util import xes

import proved.xes_keys as xes_keys


def initialize_udfg(activities):
    """
    Given a list of activity labels, initializes the structure for a udfg
    The resulting dictionary has the stucture
    activity -> (integer, integer)
    activity, activity) -> (integer, integer)

    :param activities: the list of activity labels
    :return: a dictionary initialized with the structure of a udfg
    """

    udfg = {}
    for activity1 in activities:
        udfg[activity1] = (0, 0)
        for activity2 in activities:
            udfg[(activity1, activity2)] = (0, 0)

    return udfg


def find_all_paths(origin, target):
    """
    Given a behavior graph, finds all the paths between two given nodes

    :param ts: the behavior graph
    :param origin: the starting node
    :param target: the goal node
    :return: a list of paths (list of lists of nodes)
    """

    # Explores the graph saving a list of pairs (node, [list of nodes]), so every node is traced with its path
    nodes_and_paths_to_process = [[origin]]
    hits = []
    while nodes_and_paths_to_process:
        path = nodes_and_paths_to_process.pop(0)
        last_node = path[-1]
        if last_node == target:
            hits.append(path)
        else:
            for arc in last_node.outgoing:
                if arc.to_state.name is not 'end':
                    new_path = list(path)
                    new_path.append(arc.to_state)
                    nodes_and_paths_to_process.append(new_path)

    return hits


def is_bridge(bg, state1, state2):
    """
    Checks whether the arc between two states of a behavior graph is a bridge

    :param bg: the transition system (must be a behavior graph)
    :param state1: the starting state
    :param state2: the arrival state
    :param name: the name of the transition
    :return: a boolean
    """

    # Pre-check
    if len(state1.outgoing) > 1 or len(state2.incoming) > 1:
        return False

    # Temporarily remove the arc to check
    utils.remove_all_arcs_from_to(state1, state2, bg)

    # Perform a simple breadth-first search keeping track of all the states
    discovered = set()
    to_process = [state for state in bg.states if state.name == 'start']
    while to_process:
        current_state = to_process.pop()
        for arc in current_state.outgoing:
            to_process.append(arc.to_state)
        discovered.add(current_state)

    # Re-adds the connection to avoid side-effects
    utils.add_arc_from_to(repr(state1) + repr(state2), state1, state2, bg)

    # If the number of states discovered by the procedure is less than the whole transition system
    # the arc is a bridge and we return true
    if len(bg.states) > len(discovered):
        return True
    else:
        return False


def get_activity_labels(log, activity_key=xes.DEFAULT_NAME_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
    """
    Extract the set of all possible activity labels from an uncertain event log

    :param log: the uncertain event log
    :param activity_key: the key to access the activity label
    :param u_activity_key: the key to access the uncertain activity labels
    :return: the set of possible activity labels
    """

    activity_labels = set()
    for trace in log:
        for event in trace:
            if u_activity_key not in event:
                activity_labels.add(event[activity_key])
            else:
                activity_labels = activity_labels.union(list(event[u_activity_key]['children']))

    return sorted(activity_labels)


def initialize_df_global_counts_map(activity_labels):
    """
    Initializes a map of counts given an activity labels set

    :param activity_labels: the set of possible activity labels
    :return: the map activity->(activity->(integer, integer)) to store the counts, initialized with all (0,0)
    """

    df_intervals_counts_map = {}
    for from_activity in activity_labels:
        df_intervals_counts_map[from_activity] = {}
        for to_activity in activity_labels:
            df_intervals_counts_map[from_activity][to_activity] = (0, 0)

    return df_intervals_counts_map


def initialize_df_counts_map(activity_labels):
    """
    Initializes a map of counts given an activity labels set

    :param activity_labels: the set of possible activity labels
    :return: the map activity->(activity->(integer, integer)) to store the counts, initialized with all (0,0)
    """

    df_intervals_counts_map = {}
    for from_activity in activity_labels:
        for to_activity in activity_labels:
            df_intervals_counts_map[(from_activity, to_activity)] = []

    return df_intervals_counts_map


def add_to_map(counts_map, origin, target, certain):
    """
    Given the map of counts and two nodes, adds to the map the min and max count from every activity of the first node
    to every activity of the second node

    :param counts_map: the map activity->(activity->(integer, integer)) to store the counts
    :param origin: the first node
    :param target: the second node
    :param min: the min count
    :param max: the max count
    :return:
    """
    for from_activity in [transition.label for transition in origin.data[1] if transition.label is not None]:
        for to_activity in [transition.label for transition in target.data[1] if transition.label is not None]:
            counts_map[(from_activity, to_activity)].append((origin, target, certain))
