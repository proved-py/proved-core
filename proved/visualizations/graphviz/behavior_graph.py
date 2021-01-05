import string

from graphviz import Digraph


def behavior_graph_graphviz(behavior_graph, name='bg', format='png', filename='bg', rankdir='LR'):
    """
    Returns a Graphviz visualization from a behavior graph

    :param behavior_graph: A behavior graph
    :type behavior_graph:
    :return: The Graphviz object of the behavior graph in input.
    :rtype:
    """

    g = Digraph(name, format=format, filename=filename + '.' + format)
    g.attr(rankdir=rankdir)
    for bg_node in behavior_graph.nodes:
        if None in bg_node[1]:
            g.attr('node', style='dashed')
        else:
            g.attr('node', style='solid')
        g.node(''.join([act.translate(str.maketrans('', '', string.punctuation + ' ')) for act in bg_node[1] if act is not None]) + str(bg_node[0]), label=', '.join([act for act in bg_node[1] if act is not None]))
    for bg_node1, bg_node2 in behavior_graph.edges:
        g.edge(''.join([act.translate(str.maketrans('', '', string.punctuation + ' ')) for act in bg_node1[1] if act is not None]) + str(bg_node1[0]), ''.join([act.translate(str.maketrans('', '', string.punctuation + ' ')) for act in bg_node2[1] if act is not None]) + str(bg_node2[0]))
    return g
