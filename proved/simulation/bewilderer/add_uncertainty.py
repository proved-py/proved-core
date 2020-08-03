from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY

from proved.xes_keys import DEFAULT_U_NAME_KEY, DEFAULT_U_TIMESTAMP_MIN_KEY, DEFAULT_U_TIMESTAMP_MAX_KEY, DEFAULT_U_MISSING_KEY
from proved.simulation.bewilderer.add_activities import add_uncertain_activities_to_log
from proved.simulation.bewilderer.add_timestamps import add_uncertain_timestamp_to_log
from proved.simulation.bewilderer.add_indeterminate_events import add_indeterminate_events_to_log


def add_uncertainty(p_a=0.0, p_t=0.0, p_i=0.0, log=None, log_map=None, max_labels_to_add=1, label_set=None, activity_key=DEFAULT_NAME_KEY, u_activity_key=DEFAULT_U_NAME_KEY, timestamp_key=DEFAULT_TIMESTAMP_KEY, u_timestamp_min_key=DEFAULT_U_TIMESTAMP_MIN_KEY, u_timestamp_max_key=DEFAULT_U_TIMESTAMP_MAX_KEY, u_missing_key=DEFAULT_U_MISSING_KEY):
    add_uncertain_activities_to_log(p_a, log, log_map=log_map, max_labels_to_add=max_labels_to_add, label_set=label_set, activity_key=activity_key, u_activity_key=u_activity_key)
    add_uncertain_timestamp_to_log(p_t, log, log_map=log_map, timestamp_key=timestamp_key, u_timestamp_min_key=u_timestamp_min_key, u_timestamp_max_key=u_timestamp_max_key)
    add_indeterminate_events_to_log(p_i, log, log_map=log_map, u_missing_key=u_missing_key)
