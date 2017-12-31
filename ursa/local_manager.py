import ray
import ray.local_scheduler as local_scheduler
from . import graph as ug

class Graph_manager(object):
    """
    This object manages all graphs in the system.

    Fields:
    graph_dict -- the dictionary of adjacency lists for the graphs.
                           The keys for the dictionary are the graph_ids, and
                           the values are the Graph objects.
    """
    def __init__(self):
        """
        The constructor for an Graph_collection object. Initializes some toy
        graphs as an example.
        """
        self.graph_dict = {}
        self._graph_is_updated = {}
        self._current_transaction_id = 0

    def update_transaction_id():
        """
        Updates the transaction ID with that of the global graph manager.
        """


    def add_graph(self, graph_id):
        """
        Create an empty graph.

        Keyword arguments:
        graph_id -- the name of the new graph.
        """
        self._current_transaction_id += 1

        if not graph_id or graph_id == "":
            raise ValueError("Graph must be named something.")
        if graph_id in self.graph_dict:
            raise ValueError("Graph name already exists.")
        self.graph_dict[graph_id] = ug.Graph.remote()
        self._graph_is_updated[graph_id] = []
        
    def add_node_to_graph(self, graph_id, key, node, adjacency_list = set(), connections_to_other_graphs = {}):
        """
        Adds data to the graph specified.

        Keyword arguments:
        graph_id -- the unique name of the graph.
        key -- the unique identifier of this data in the graph.
        node -- the data to add to the graph.
        adjacency_list -- a list of connected nodes, if any (default = set()).
        """
        self._current_transaction_id += 1

        if type(connections_to_other_graphs) is not dict:
            raise ValueError("Connections between graphs must be labeled with a destination graph.")

        if graph_id not in self.graph_dict:
            print("Warning:", str(graph_id), "is not yet in this Graph Collection. Creating...")
            self.add_graph(graph_id)

        self._graph_is_updated[graph_id].append(_add_node_to_graph.remote(self.graph_dict[graph_id],
                                                                      graph_id,
                                                                      key,
                                                                      node,
                                                                      adjacency_list,
                                                                      connections_to_other_graphs))

        self._graph_is_updated[graph_id].append(_add_back_edges_within_graph.remote(self.graph_dict[graph_id],
                                                                                graph_id,
                                                                                key,
                                                                                adjacency_list))

        for other_graph_id in connections_to_other_graphs:
            if not other_graph_id in self.graph_dict:
                print("Warning:", str(new_conn), "is not yet in this Graph Collection. Creating...")
                self.add_graph(other_graph_id)

            try:
                connections_to_this_graph = set([connections_to_other_graphs[other_graph_id]])
            except TypeError:
                connections_to_this_graph = set(connections_to_other_graphs[other_graph_id])

            self._graph_is_updated[other_graph_id].append(_add_back_edges_between_graphs.remote(self.graph_dict[other_graph_id],
                                                                                            key,
                                                                                            graph_id,
                                                                                            connections_to_this_graph))

    def append_to_connections(self, graph_id, key, adjacent_node_key):
        """
        Adds a new connection to the graph for the key provided.

        Keyword arguments:
        graph_id -- the unique name of the graph.
        key -- the unique identifier of the node in the graph.
        new_adjacent_node_key -- the unique identifier of the new connection.
        """
        self._current_transaction_id += 1

        self.graph_dict[graph_id].add_new_adjacent_node.remote(key, 
                                                               adjacent_node_key)
        
    def add_inter_graph_connection(self, graph_id, key, other_graph_id, other_graph_key):
        """
        Adds a new connection to another graph. Because all connections
        are bi-directed, connections are created from the other graph to this
        one also.

        Keyword arguments:
        graph_id -- the unique name of the graph.
        key -- the unique identifier of the node in the graph.
        other_graph_id -- the unique name of the graph to connect to.
        other_graph_key -- the unique identifier of the node to connect to.
        """
        self._current_transaction_id += 1

        self.graph_dict[graph_id].add_inter_graph_connection.remote(key,
                                                                    other_graph_id,
                                                                    other_graph_key)

        # Adding this back edge to satisfy the bi-directionality requirement
        self.graph_dict[other_graph_id].add_inter_graph_connection.remote(other_graph_key,
                                                                          graph_id,
                                                                          key)

    def add_multiple_inter_graph_connections(self, graph_id, key, other_graph_id, collection_of_other_graph_keys):
        """
        Adds multiple new connections to another graph.

        Keyword arguments:
        graph_id -- the unique name of the graph.
        key -- the unique identifier of the node in the graph.
        other_graph_id -- the unique name of the graph to connect to.
        collection_of_other_graph_keys -- the collection of unique identifier
                                          of the node to connect to.
        """
        self._current_transaction_id += 1

        self.graph_dict[graph_id].add_multiple_inter_graph_connections.remote(key,
                                                                              other_graph_id,
                                                                              collection_of_other_graph_keys)

        self._graph_is_updated[other_graph_id].append(_add_back_edges_between_graphs.remote(self.graph_dict[other_graph_id],
                                                                                        key,
                                                                                        graph_id,
                                                                                        collection_of_other_graph_keys))

    def node_exists(self, graph_id, key):
        """
        Determines whether or not a node exists in the graph.

        Keyword arguments:
        graph_id -- the unique name of the graph
        key -- the unique identifier of the node in the graph.

        Returns:
        True if both the graph exists and the node exists in the graph,
        false otherwise
        """
        return graph_id in self.graph_dict and self.graph_dict[graph_id].node_exists.remote(key)
    
    def get_node(self, graph_id, key):
        """
        Gets the ObjectID for a node in the graph requested.

        Keyword arguments:
        graph_id -- the unique name of the graph.
        key -- the unique identifier of the node in the graph.

        Returns:
        The Ray ObjectID from the graph and key combination requested.
        """

        ray.get(self._graph_is_updated[graph_id])
        self._graph_is_updated[graph_id] = []

        return self.graph_dict[graph_id].get_oid_dictionary.remote(key)
    
    def get_inter_graph_connections(self, graph_id, key, other_graph_id = ""):
        """
        Gets the connections between graphs for the node requested. Users can
        optionally specify the other graph they are interested in.

        Keyword arguments:
        graph_id -- the unique name of the graph.
        key -- the unique identifier of the node in the graph.
        other_graph_id -- the name of the other graph (default = "")

        Returns:
        When other_graph_id is "", all connections between graphs for
        the graph and key requested. Otherwise, the connections for the
        graph specified in other_graph_id for the graph and key requested.
        """

        ray.get(self._graph_is_updated[graph_id])
        self._graph_is_updated[graph_id] = []

        if other_graph_id == "":
            return self.graph_dict[graph_id].get_inter_graph_connections.remote(key)
        else:
            return self.graph_dict[graph_id].get_inter_graph_connections.remote(key,
                                                                                other_graph_id)
        
    def get_graph(self, graph_id):
        """
        Gets the graph requested.

        Keyword arguments:
        graph_id -- the unique name of the graph.

        Returns:
        The Graph object for the graph requested.
        """

        ray.get(self._graph_is_updated[graph_id])
        self._graph_is_updated[graph_id] = []

        return self.graph_dict[graph_id]

    def get_adjacency_list(self, graph_id, key):
        """
        Gets the adjacency list for the graph and key requested.

        Keyword arguments:
        graph_id -- the unique name of the graph.
        key -- the unique identifier of the node in the graph.

        Returns:
        The list of all connections within the same graph for the node
        requested.
        """

        ray.get(self._graph_is_updated[graph_id])
        self._graph_is_updated[graph_id] = []

        return self.graph_dict[graph_id].get_adjacency_list.remote(key)

@ray.remote
def _add_node_to_graph(graph, graph_id, key, node, adjacency_list, connections_to_other_graphs):
    """
    Adds a node to the graph provided and associates it with the connections.

    Keyword arguments:
    graph -- the Graph object to add the node to.
    graph_id -- the unique identifier of the Graph provided.
    key -- the unique identifier of the node provided.
    node -- the Node object to add to the graph.
    adjacency_list -- the list of connections within this graph.
    """
    graph.insert_node_into_graph.remote(key, node, adjacency_list, connections_to_other_graphs)
    return True  

@ray.remote
def _add_back_edges_within_graph(graph, graph_id, key, new_connection_list):
    """
    Adds back edges to the connections provided. This achieves the
    bi-drectionality guarantees we have.

    Keyword arguments:
    graph -- the Graph object to add the back edges to.
    graph_id -- the unique identifier of the graph provided.
    key -- the unique identifier of the Node to connect back edges to.
    new_connection_list -- the list of connections to create back edges for.
    """
    for new_conn in new_connection_list:
        graph.add_new_adjacent_node.remote(key, new_conn)

    return True

@ray.remote
def _add_back_edges_between_graphs(other_graph, key, graph_id, collection_of_other_graph_keys):
    """
    Given a list of keys in another graph, creates connections to the key
    provided. This is used to achieve the bi-drectionality in the graph.

    Keyword arguments:
    other_graph -- the Graph object of the other graph for the connections to
                   be added.
    key -- the key to connect the other graph keys to.
    graph_id -- the unique identifier of the graph to connect to.
    collection_of_other_graph_keys -- the keys in other_graph to connect to key.
    """
    for other_graph_key in collection_of_other_graph_keys:
        other_graph.add_inter_graph_connection.remote(other_graph_key, graph_id, key)

    return True
