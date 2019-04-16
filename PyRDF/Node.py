from __future__ import print_function
from PyRDF.Operation import Operation
from PyRDF.Proxy import ActionProxy, TransformationProxy


class Node(object):
    """
    A Class that represents a node in RDataFrame operations graph. A Node
    houses an operation and has references to children nodes.
    For details on the types of operations supported, try :

    import PyRDF
    PyRDF.use(...) # Choose your backend
    print(PyRDF.current_backend.supported_operations)

    Attributes
    ----------
    get_head : function
        A lambda function that returns the head
        node of the current graph.

    operation
        The operation that this Node represents. This
        could be `None`.

    children
        A list of `Node` objects which represent the
        children nodes connected to the current node.

    value
        The computed value after executing the operation in
        the current node for a particular PyRDF graph. This
        is permanently `None` for transformation nodes and
        the action nodes get a `RResultPtr` after event-loop
        execution.

    pyroot_node
        Reference to the PyROOT object that implements the
        functionality of this node on the cpp side.

    has_user_references
        A flag to check whether the node has direct user references, that is
        if it is assigned to a variable. Default value is `True`, turns to
        `False` if the proxy that wraps the node gets garbage collected by
        Python.
    """

    def __init__(self, get_head, operation):
        """
        Creates a new `Node` based on the 'operation'.

        Parameters
        ----------
        get_head : function
            A lambda function that returns the head
            node of the current graph. This value
            could be `None`.

        operation : PyRDF.Operation.Operation
            The operation that this Node represents. This
            could be `None`.
        """
        if get_head is None:
            # Function to get 'head' Node
            self.get_head = lambda: self
        else:
            self.get_head = get_head

        self.operation = operation
        self.children = []
        self._cur_attr = ""  # Name of the new incoming operation
        self.value = None
        self.pyroot_node = None
        self.has_user_references = True  # Flag for pruning

    def __getstate__(self):
        """
        Converts the state of the current node
        to a Python dictionary.

        Returns
        -------
        dictionary
            A dictionary that stores all instance variables
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

        Parameters
        ----------
        state : dictionary
            This is the state dictionary that needs to
            be converted to a `Node` object.

        """
        self.children = state['children']
        if state.get('operation_name'):
            self.operation = Operation(state['operation_name'],
                                       *state['operation_args'],
                                       **state["operation_kwargs"])
        else:
            self.operation = None

    def __getattr__(self, attr):
        """
        Intercepts any non-dunder call to the current node
        and dispatches it by means of a call handler.

        Parameters
        ----------
        attr : str
            The name of the operation in the new
            child node.

        Returns
        -------
        function
            A method to handle an operation call to the
            current node.

        """
        self._cur_attr = attr  # Stores new operation name

        # Check if the current call is a dunder method call
        import re
        if re.search("^__[a-z]+__$", attr):
            # Raise an AttributeError for all dunder method calls
            raise AttributeError("Such an attribute is not set ! ")

        from . import current_backend
        if self._cur_attr not in current_backend.supported_operations:
            raise AttributeError("Attribute does not exist")
        return self._call_handler

    def _call_handler(self, *args, **kwargs):
        # Handles an operation call to the current node and
        # returns the new node built using the operation call.

        from . import current_backend
        # Check if the current operation is supported by
        # the backend
        current_backend.check_supported(self._cur_attr)

        # Create a new `Operation` object for the
        # incoming operation call
        op = Operation(self._cur_attr, *args, **kwargs)

        # Create a new `Node` object to house the operation
        newNode = Node(operation=op, get_head=self.get_head)

        # Add the new node as a child of the current node
        self.children.append(newNode)

        # Return the appropriate proxy object for the node
        if op.is_action():
            return ActionProxy(newNode)
        else:
            return TransformationProxy(newNode)

    def is_prunable(self):
        """
        Checks whether the current node can be pruned from the computational
        graph.

        Returns
        -------
        bool
            True if the node has no children and no user references or its
            value has already been computed, False otherwise.
        """

        if not self.children:
            # Every pruning condition is written on a separate line
            if not self.has_user_references or \
               (self.operation and self.operation.is_action() and self.value):

                # ***** Condition 1 *****
                # If the node is wrapped by a proxy which is not directly
                # assigned to a variable, then it will be flagged for pruning

                # ***** Condition 2 *****
                # If the current node's value was already
                # computed, it should get pruned only if it's
                # an Action node.
                return True

        return False

    def graph_prune(self):
        """
        Prunes nodes from the current PyRDF graph under certain conditions.
        The current node will be pruned if it has no children and the user
        application does not hold any reference to it. The children of the
        current node will get recursively pruned.

        Returns
        -------
        bool
            True if the current node has to be pruned, False otherwise.

        """
        children = []

        for n in self.children:
            # Select children based on pruning condition

            if not n.graph_prune():
                children.append(n)

        self.children = children
        return self.is_prunable()
