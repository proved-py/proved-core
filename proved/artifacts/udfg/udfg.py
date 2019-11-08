from pm4py.objects.log.util import xes
from networkx.algorithms.traversal.breadth_first_search import bfs_successors
from networkx.algorithms.bridges import bridges

import proved.xes_keys as xes_keys
from proved.algorithms.conformance.alignments.utils import construct_behavior_graph
from proved.artifacts.udfg.utils import get_activity_labels, is_bridge, find_all_paths, add_to_map, initialize_df_counts_map, \
    initialize_df_global_counts_map


class Udfg(dict):

    def __init__(self, log=None):

        dict.__init__(self)
        self.__activities = []

        if log is not None:
            self.__set_activities(log)
            self.__init__(initialize_udfg(self.activities))
            # self.update(get_activities_interval_counts(log, self.activities))
            get_activities_counts_log(self, log)
            # TODO: change get_activities_interval_counts_new from activity->(activity->(integer, integer))
            # TODO: to (activity, activity)->(integer, integer) and merge it with self
            # self.update(get_activities_interval_counts(log, self.activities))
            get_df_counts_log(self, log)
            # get_directly_follow_intervals_log(self, log, self.activities)

    def __set_activities(self, log):
        self.__activities = get_activity_labels(log)

    def __get_activities(self):
        return self.__activities

    activities = property(__get_activities, __set_activities)


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


def get_activities_counts_log(udfg, log):
    for bg, n in log:
        get_activities_counts_trace(bg, n, udfg)


def get_activities_counts_trace(udfg, bg, n=1):
    for node in bg.nodes:
        if len(node) == 1:
            activity_label = next(iter(node))
            udfg[activity_label] = (
                udfg[activity_label][0] + n,
                udfg[activity_label][1] + n
            )
        else:
            for activity_label in node - {'START', 'END', None}:
                udfg[activity_label] = (
                    udfg[activity_label][0],
                    udfg[activity_label][1] + n
                )


def get_df_counts_log(udfg, log):
    for bg, n in log:
        get_df_counts_trace(bg, n, udfg)


# TODO: modify the implementation so that instead of selecting a pair of activities first and then search, it starts with the
# search and then for each pair of node it iterates on their activity labels
# TODO: this does not take into account indeterminate events! Complete the subsearch for long-distance bindings!
def get_df_counts_trace(udfg, bg, n=1):
    # Fetches all the activities in the uncertain trace
    bg_activities = set.union(*bg.nodes) - {None}  # TODO: specifically check this
    # Fetches all the bridges in the behavior graph
    bg_bridges = bridges(bg)
    # Checks the number of directly-follows relationships for each pair of activities in the uncertain trace
    for activity_from in bg_activities:
        for activity_to in bg_activities:
            # Lists to keep track of nodes already bound in a directly follows relationship
            used_left = set()
            used_right = set()
            for node_from, successors in bfs_successors(bg, bg.root):
                # Check if a directly-follows occurs in all realizations of the uncertain trace
                for node_to in successors:
                    if node_from == {activity_from} and node_to == {activity_to} and (node_from, node_to) in bg_bridges:
                        if (
                            activity_from != activity_to and {node_from, node_to}.isdisjoint(used_left | used_right)
                        ) or (
                            activity_from == activity_to and node_from not in used_left and node_to not in used_right
                        ):
                            udfg[(activity_from, activity_to)] = (
                                udfg[(activity_from, activity_to)][0] + n,
                                udfg[(activity_from, activity_to)][1] + n
                            )
                            used_left.add(node_from)
                            used_right.add(node_to)
                            break
                # If not, we look for a directly-follows relationship that only occurs on some realizations
                node_to_candidates = successors  # TODO: maybe needs a shallow copy
                while node_to_candidates:
                    for node_to in node_to_candidates:
                        if activity_from in node_from and activity_to in node_to:
                            if (
                                activity_from != activity_to and {node_from, node_to}.isdisjoint(used_left | used_right)
                            ) or (
                                activity_from == activity_to and node_from not in used_left and node_to not in used_right
                            ):
                                udfg[(activity_from, activity_to)] = (
                                    udfg[(activity_from, activity_to)][0],
                                    udfg[(activity_from, activity_to)][1] + n
                                )
                                used_left.add(node_from)
                                used_right.add(node_to)
                                break
                    node_to_candidates = set.union(*[node.successor for node in node_to_candidates if None in node])






















































def get_directly_follow_intervals_nodes(map, origin, target, bg):
    """
    Counts the minimum and maximum number of occurrences of directly-follows relationships between two given nodes of
    a behavior graph

    :param map: the map activity->(activity->(integer, integer)) to store the counts
    :param origin: the origin node
    :param target: the target node
    :return:
    """

    paths_forward = find_all_paths(origin, target)
    paths_backward = find_all_paths(target, origin)

    if not paths_forward and not paths_backward:
        # add_to_map(map, origin, target, 0, 1)
        add_to_map(map, origin, target, False)
        # add_to_map(map, target, origin, 0, 1)

    if paths_forward:
        if paths_forward == [[origin, target]]:
            # Arco diretto tra i due nodi: se l'attività di entrambi non è uncertain e sono tutti e due ! e l'arco tra
            # i due nodi è un bridge aggiungo (1, 1), altrimenti aggiungo (0, 1)
            if len(origin.data[1]) == 1 and len(
                target.data[1]) == 1 and 'ε' not in origin.name and 'ε' not in target.name and is_bridge(bg, origin,
                                                                                                         target):
                # add_to_map(map, origin, target, 1, 1)
                add_to_map(map, origin, target, True)
            else:
                # add_to_map(map, origin, target, 0, 1)
                add_to_map(map, origin, target, False)
        else:
            # Percorsi tra origin e target: se almeno un percorso è fatto tutto di eventi ? (tranne origin e target)
            # aggiungo (0, 1), altrimenti aggiungo (0, 0)
            for path in paths_forward:
                found_det = False
                for node in path[1:-1]:
                    if 'ε' not in node.name:
                        found_det = True
                if not found_det:
                    # add_to_map(map, origin, target, 0, 1)
                    add_to_map(map, origin, target, False)
                    continue

    # # Procedimento esattamente identico e simmetrico per l'altra direzione
    # if paths_backward:
    #     if paths_backward == [[target, origin]]:
    #         # Arco diretto tra i due nodi: se l'attività di entrambi non è uncertain e sono tutti e due ! e l'arco tra
    #         # i due nodi è un bridge aggiungo (1, 1), altrimenti aggiungo (0, 1)
    #         if len(target.data[1]) == 1 and len(
    #                 origin.data[1]) == 1 and 'ε' not in target.name and 'ε' not in origin.name and not is_bridge(bg,
    #                                                                                                              target,
    #                                                                                                              origin):
    #             add_to_map(map, target, origin, 1, 1)
    #         else:
    #             add_to_map(map, target, origin, 0, 1)
    #     else:
    #         # Percorsi tra origin e target: se almeno un percorso è fatto tutto di eventi ? (tranne origin e target)
    #         # aggiungo (0, 1), altrimenti aggiungo (0, 0)
    #         for path in paths_backward[1:-1]:
    #             found_det = False
    #             for node in path:
    #                 if 'ε' in node.name:
    #                     found_det = True
    #             if not found_det:
    #                 add_to_map(map, target, origin, 0, 1)
    #                 continue


def get_directly_follow_intervals_trace(map, trace):
    """
    Counts the minimum and maximum number of occurrences of directly-follows relationships within an uncertain trace

    :param map: the map activity->(activity->(integer, integer)) to store the counts
    :param trace: the uncertain trace to be examined
    :return:
    """

    bg = construct_behavior_graph(trace)
    states = [state for state in bg.states if state.name is not 'start' and state.name is not 'end']

    for i in range(len(states) - 1):

        for j in range(i + 1, len(states)):
            get_directly_follow_intervals_nodes(map, states[i], states[j], bg)
            get_directly_follow_intervals_nodes(map, states[j], states[i], bg)


def get_directly_follow_intervals_log(map, log, activities):
    """
    Counts the minimum and maximum number of occurrences of directly-follows relationships within an uncertain trace

    :param map: the map activity->(activity->(integer, integer)) to store the counts
    :param log: the uncertain event log to be examined
    :return:
    """

    for trace in log:
        df_intervals_counts_map = initialize_df_counts_map(activities)
        get_directly_follow_intervals_trace(df_intervals_counts_map, trace)
        interpret_counts_and_add(map, df_intervals_counts_map)


def get_activities_interval_counts(log, activity_labels, activity_key=xes.DEFAULT_NAME_KEY,
                                   u_missing=xes_keys.DEFAULT_U_MISSING_KEY, u_activity_key=xes_keys.DEFAULT_U_NAME_KEY):
    """
    Counts the minimum and maximum number of occurrences of activities in an uncertain event log

    :param log: the uncertain event log
    :param activity_labels: the set of possible activity labels
    :param activity_key: the key to access the activity label
    :param u_activity_key: the key to access the uncertain activity labels
    :return: the map activity->(integer, integer) to store the counts
    """

    activity_intervals_counts_map = {}
    for activity_label in activity_labels:
        activity_intervals_counts_map[activity_label] = (0, 0)

    for trace in log:
        for event in trace:
            if u_activity_key not in event:
                if u_missing not in event:
                    activity_intervals_counts_map[event[activity_key]] = (
                        activity_intervals_counts_map[event[activity_key]][0] + 1,
                        activity_intervals_counts_map[event[activity_key]][1] + 1)
                else:
                    activity_intervals_counts_map[event[activity_key]] = (
                        activity_intervals_counts_map[event[activity_key]][0],
                        activity_intervals_counts_map[event[activity_key]][1] + 1)
            else:
                for activity_label in list(event[u_activity_key]['children']):
                    activity_intervals_counts_map[activity_label] = (activity_intervals_counts_map[activity_label][0],
                                                                     activity_intervals_counts_map[activity_label][
                                                                         1] + 1)

    return activity_intervals_counts_map


def slice_udfg(act_map, rel_map, act_min, act_max, rel_min, rel_max):
    """
    Builds a directly-follows graph by filtering the relationships according to the filtering parameters

    :param act_map: the map containing the interval counts of activities
    :param rel_map: the map containing the interval counts of directly-follows relations
    :param act_min: minimum value for ratios of activity interval counts
    :param act_max: maximum value for ratios of activity interval counts
    :param rel_min: minimum value for ratios of directly-follows interval counts
    :param rel_max: maximum value for ratios of directly-follows interval counts
    :return: a directly-follows graph
    """

    filtered_activities = [activity for activity in act_map.keys() if
                           act_min <= act_map[activity][0] / act_map[activity][1] <= act_max]

    # for activity in act_map.keys():
    #     print(activity)
    #     print(str(act_map[activity][0]) + '   ' + str(act_map[activity][1]) + '   ' + str(act_map[activity][0] / act_map[activity][1]))

    # print(list(act_map))
    dfg = []
    for source in rel_map.keys():
        # print(source)
        for target in rel_map[source].keys():
            # print(target)
            if rel_map[source][target][1] != 0:
                # print('pippo')
                if rel_min <= rel_map[source][target][0] / rel_map[source][target][
                    1] <= rel_max and source in filtered_activities and target in filtered_activities:
                    # print('pluto')
                    dfg.append(((source, target), 1))

    return dfg


# def directly_follow_intervals_trace_old(map, trace):
#     """
#     Counts the minimum and maximum number of occurrences of directly-follows relationships within an uncertain trace
#
#     :param map: the map activity->(activity->(integer, integer)) to store the counts
#     :param trace: the uncertain trace to be examined
#     :return:
#     """
#
#     ts = construct_behavior_graph(trace)
#
#     # Perform a breadth-first search to select the origin node
#     completed = []
#     to_process = [state for state in ts.states if state.name == 'start']
#     while len(to_process) != 0:
#         origin = to_process.pop(0)
#
#         ## Starting from origin, computes the min and max values for the activities of every other reachable node
#         # Initializing the list of descendants to compare. I save the full path, rather than just the node (type list)
#         to_compare = []
#         for arc in origin.outgoing:
#             to_compare += [[state] for state in arc.to_state]
#
#         while to_compare:
#             current_path = to_compare.pop(0)
#             current_node = current_path.pop()
#
#             # DA QUI IN POI CI VANNO TUTTI I CONTROLLI CHE HO SEGNATO SUL QUADERNO, PAGINA 7
#             if len(current_path) == 1:
#                 # SE ARRIVO QUI DENTRO VUOL DIRE CHE LA COPPIA DI NODI CHE STO CONTROLLANDO È "CONSECUTIVA", È LINKATA DA UN SOLO ARCO
#
#
#         for arc in origin.outgoing:
#             to_process += arc.to_state
#         completed.append(origin)

def interpret_counts_and_add(global_map, trace_map):
    for act1, act2 in trace_map.keys():
        if act1 == act2:
            if trace_map[(act1, act2)]:
                used_origin_states = set()
                used_target_states = set()
                for origin, target, certainty in trace_map[(act1, act2)]:
                    if origin not in used_origin_states and target not in used_target_states:
                        if certainty:
                            global_map[act1][act2] = (global_map[act1][act2][0] + 1, global_map[act1][act2][1] + 1)
                        else:
                            global_map[act1][act2] = (global_map[act1][act2][0], global_map[act1][act2][1] + 1)
                        used_origin_states.add(origin)
                        used_target_states.add(target)
        else:
            if trace_map[(act1, act2)]:
                used_states = set()
                for origin, target, certainty in trace_map[(act1, act2)]:
                    if origin not in used_states and target not in used_states:
                        if certainty:
                            global_map[act1][act2] = (global_map[act1][act2][0] + 1, global_map[act1][act2][1] + 1)
                        else:
                            global_map[act1][act2] = (global_map[act1][act2][0], global_map[act1][act2][1] + 1)
                        used_states.add(origin)
                        used_states.add(target)
