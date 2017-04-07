from functools import reduce
import operator
import numpy as np


class Node(object):
    def __init__(self, inbound_nodes=[]):
        self.inbound_nodes = inbound_nodes
        self.outbound_nodes = []
        self.value = None
        self.gradients = {}
        # this new node is part of the outbound_nodes of each inbound_nodes
        for n in self.inbound_nodes:
            n.outbound_nodes.append(self)

    def forward(self):
        """
        Forward propagation
        Every subclass needs to implement it
        """
        raise NotImplementedError

    def backward(self):
        """
        Backward propagation
        Every subclass needs to implement it
        """
        raise NotImplementedError


class Input(Node):
    def __init__(self, x=None):
        Node.__init__(self)

    # Only the Input node can accept a value as in input of the forward function.
    # Also it does not compute anything and can just hold the `value`
    def forward(self, value=None):
        if value is not None:
            self.value = value

    def backward(self):
        # An Input node has no inputs so the gradient (derivative)
        # is zero.
        # The key, `self`, is reference to this object.
        self.gradients = {self: 0}
        # Weights and bias may be inputs, so you need to sum
        # the gradient from output gradients.
        for n in self.outbound_nodes:
            grad_cost = n.gradients[self]
            self.gradients[self] += grad_cost * 1


class Add(Node):
    def __init__(self, *x_list):
        Node.__init__(self, inbound_nodes=[x for x in x_list])

    def forward(self):
        self.value = sum(map(lambda n: n.value, self.inbound_nodes))

    def backward(self):
        pass


class Mul(Node):
    def __init__(self, *x_list):
        Node.__init__(self, inbound_nodes=[x for x in x_list])

    def forward(self):
        self.value = reduce(operator.mul, (map(lambda n: n.value, self.inbound_nodes)))

    def backward(self):
        pass


class Linear(Node):
    def __init__(self, inputs, weights, bias):
        Node.__init__(self, inbound_nodes=[inputs, weights, bias])

    def forward(self):
        X = self.inbound_nodes[0].value
        W = self.inbound_nodes[1].value
        b = self.inbound_nodes[2].value
        self.value = X.dot(W) + b

    def backward(self):
        """
        Calculates the gradient based on the output values.
        """
        # Initialize a partial for each of the inbound_nodes.
        self.gradients = {n: np.zeros_like(n.value) for n in self.inbound_nodes}
        # Cycle through the outputs. The gradient will change depending
        # on each output, so the gradients are summed over all outputs.
        for n in self.outbound_nodes:
            # Get the partial of the cost with respect to this node.
            grad_cost = n.gradients[self]
            # Set the partial of the loss with respect to this node's inputs.
            self.gradients[self.inbound_nodes[0]] += np.dot(grad_cost, self.inbound_nodes[1].value.T)
            # Set the partial of the loss with respect to this node's weights.
            self.gradients[self.inbound_nodes[1]] += np.dot(self.inbound_nodes[0].value.T, grad_cost)
            # Set the partial of the loss with respect to this node's bias.
            self.gradients[self.inbound_nodes[2]] += np.sum(grad_cost, axis=0, keepdims=False)


class Sigmoid(Node):
    def __init__(self, linear):
        Node.__init__(self, inbound_nodes=[linear])

    def _sigmoid(self, x):
        return 1. / (1. + np.exp(-x))

    def forward(self):
        linear = self.inbound_nodes[0].value
        self.value = self._sigmoid(linear)

    def backward(self):
        """
        Calculates the gradient using the derivative of
        the sigmoid function.
        """
        # Initialize the gradients to 0.
        self.gradients = {n: np.zeros_like(n.value) for n in self.inbound_nodes}

        # Cycle through the outputs. The gradient will change depending
        # on each output, so the gradients are summed over all outputs.
        for n in self.outbound_nodes:
            # Get the partial of the cost with respect to this node.
            grad_cost = n.gradients[self]
            sigmoid = self.value
            # Set the partial of the loss with respect to this node linear input.
            self.gradients[self.inbound_nodes[0]] += sigmoid * (1-sigmoid) * grad_cost


class MSE(Node):
    def __init__(self, y, a):
        Node.__init__(self, [y, a])

    def forward(self):
        y = self.inbound_nodes[0].value.reshape(-1, 1)
        a = self.inbound_nodes[1].value.reshape(-1, 1)
        self.m = self.inbound_nodes[0].value.shape[0]
        self.diff = y - a
        self.value = np.mean(self.diff ** 2)

    def backward(self):
        """
        Calculates the gradient of the cost.

        This is the final node of the network so outbound nodes
        are not a concern.
        """
        self.gradients[self.inbound_nodes[0]] = (2 / self.m) * self.diff
        self.gradients[self.inbound_nodes[1]] = (-2 / self.m) * self.diff


def topological_sort(feed_dict):
    input_nodes = [n for n in feed_dict.keys()]
    nodes = [n for n in input_nodes]
    G = {}

    while len(nodes) > 0:
        n = nodes.pop(0)
        if n not in G:
            G[n] = {'in': set(), 'out': set()}
        for m in n.outbound_nodes:
            if m not in G:
                G[m] = {'in': set(), 'out': set()}
            G[n]['out'].add(m)
            G[m]['in'].add(n)
            nodes.append(m)

    L = []
    S = set(input_nodes)
    while len(S) > 0:
        n = S.pop()

        if isinstance(n, Input):
            n.value = feed_dict[n]

        L.append(n)
        for m in n.outbound_nodes:
            G[n]['out'].remove(m)
            G[m]['in'].remove(n)
            # if no other incoming edges add to S
            if len(G[m]['in']) == 0:
                S.add(m)
    return L


def forward_pass(output_node, sorted_nodes):
    """
    Performs a forward pass through a list of sorted nodes
    :param output_node:output node of the neural network
    :param sorted_nodes:input of topological sorted nodes of the neural network
    :return:output_node value
    """
    for n in sorted_nodes:
        n.forward()

    return output_node.value


# def forward_pass(graph):
#     for n in graph:
#             n.forward()


def forward_and_backward(graph):
    """
    Performs a forward pass and a backward pass through a list of sorted Nodes.

    Arguments:

        `graph`: The result of calling `topological_sort`.
    """
    # Forward pass
    for n in graph:
        n.forward()

    # Backward pass
    for n in graph[::-1]:
        n.backward()
