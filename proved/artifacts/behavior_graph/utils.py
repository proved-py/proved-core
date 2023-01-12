import importlib


def get_quantiles(function, args, p=.01):
    """
    Retrieves the quantiles of the given probability function over the given probability.
    """

    module_name, class_name = function.rsplit('.', 1)
    if module_name == 'scipy.stats':
        minimum = getattr(importlib.import_module(module_name), class_name).ppf(**{**args, 'q': p})
        maximum = getattr(importlib.import_module(module_name), class_name).ppf(**{**args, 'q': 1 - p})
        return minimum, maximum
    elif module_name == 'numpy.random':
        raise NotImplementedError('numpy.random not yet supported.')  # TODO: add numpy.random support
    else:
        raise ValueError('Data contains an unsupported library for probability density functions.')
