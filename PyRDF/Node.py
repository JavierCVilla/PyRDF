from __future__ import print_function
from PyRDF.Operation import Operation


class Node(object):
    """
    A Class that represents a node in RDataFrame operations graph. A Node
    houses an operation and has references to children nodes.
    For details on the types of operations supported, try :

    Example::

        import PyRDF
        PyRDF.use(...) # Choose your backend
        print(PyRDF.current_backend.supported_operations)

    Attributes:
        get_head (function): A lambda function that returns the head node of
            the current graph.

        operation: The operation that this Node represents.
            This could be :obj:`None`.

        children (list): A list of :obj:`PyRDF.Node` objects which represent
            the children nodes connected to the current node.

        _new_op_name (str): The name of the new incoming operation of the next
            child, which is the last child node among the current node's
            children.

        value: The computed value after executing the operation in the current
            node for a particular PyRDF graph. This is permanently :obj:`None`
            for transformation nodes and the action nodes get a
            :obj:`ROOT.RResultPtr` after event-loop execution.

        pyroot_node: Reference to the PyROOT object that implements the
            functionality of this node on the cpp side.

        has_user_references (bool): A flag to check whether the node has
            direct user references, that is if it is assigned to a variable.
            Default value is :obj:`True`, turns to :obj:`False` if the proxy
            that wraps the node gets garbage collected by Python.
    """
    def __init__(self, get_head, operation, *args):
        """
        Creates a new node based on the operation passed as argument.

        Args:
            get_head (function): A lambda function that returns the head node
                of the current graph. This value could be `None`.

            operation (PyRDF.Operation.Operation): The operation that this Node
                represents. This could be :obj:`None`.
        """
        if get_head is None:
            # Function to get 'head' Node
            self.get_head = lambda: self
        else:
            self.get_head = get_head

        self.operation = operation
        self.children = []
        self._new_op_name = ""
        self.value = None
        self.ResultPtr = None
        self.pyroot_node = None
        self.has_user_references = True

    def __getstate__(self):
        """
        Converts the state of the current node
        to a Python dictionary.

        Returns:
            dictionary: A dictionary that stores all instance variables
            that represent the current PyRDF node.

        """
        state_dict = {'children': self.children}
        if self.operation:
            state_dict['operation_name'] = self.operation.name
            state_dict['operation_args'] = self.operation.args
            state_dict['operation_kwargs'] = self.operation.kwargs

        return state_dict

    def __setstate__(self, state):
        """
        Retrieves the state dictionary of the current
        node and sets the instance variables.

        Args:
            state (dict): This is the state dictionary that needs to be
                converted to a `Node` object.

        """
        self.children = state['children']
        if state.get('operation_name'):
            self.operation = Operation(state['operation_name'],
                                       *state['operation_args'],
                                       **state["operation_kwargs"])
        else:
            self.operation = None

    def is_prunable_action(self):
        """
        Checks if an action node can be pruned. Action nodes whose value was
        already computed can be pruned.

        Returns:
            bool: True if the node is an action and its value was already
            computed, False otherwise.
        """
        return self.operation and self.operation.is_action() and self.value

    def is_prunable_info(self):
        """
        Checks if an info node can be pruned. Info nodes whose ResultPtr was
        already assigned can be pruned.

        Returns:
            bool: True if the node is an action and its value was already
            computed, False otherwise.
        """
        return self.operation and self.operation.is_info() and self.ResultPtr

    def is_prunable_node(self):
        """
        Checks whether the current node can be pruned from the computational
        graph.

        Returns:
            bool: True if the node has no children and no user references or
            its value has already been computed, False otherwise.
        """
        if not self.children:
            # Every pruning condition is written on a separate line
            if not self.has_user_references or \
                self.is_prunable_action() or self.is_prunable_info():

                # ***** Condition 1 *****
                # If the node is wrapped by a proxy which is not directly
                # assigned to a variable, then it will be flagged for pruning

                # ***** Condition 2 *****
                # If the current node's value was already
                # computed, it should get pruned only if it's
                # an Action node.

                # ***** Condition 3 *****
                # If the current node's value was already
                # computed, it should get pruned only if it's
                # an Info operation.
                return True
        return False

    def graph_prune(self):
        """
        Prunes nodes from the current PyRDF graph under certain conditions.
        The current node will be pruned if it has no children and the user
        application does not hold any reference to it. The children of the
        current node will get recursively pruned.

        Returns:
            bool: True if the current node has to be pruned, False otherwise.
        """
        children = []

        for n in self.children:
            # Select children based on pruning condition
            if not n.graph_prune():
                children.append(n)

        self.children = children
        return self.is_prunable_node()
