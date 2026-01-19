from collections import OrderedDict
from copy import deepcopy
from typing import Dict


def ordered_dict_to_dict(variables: OrderedDict) -> Dict:
    variables = dict(deepcopy(variables))
    for key, value in variables.items():
        if type(value) == OrderedDict:
            variables[key] = ordered_dict_to_dict(value)
    return variables
