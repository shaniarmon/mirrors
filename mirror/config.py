import json
import types


NO_DEFAULT = object()
DEFAULT_VALUE = object()


def load_config(filename):
    with open(filename) as f:
        return json.load(f)


def get_config_value(config, path, default=NO_DEFAULT):
    current_config = config
    for nesting_level in path.split("."):
        current_config = current_config.get(nesting_level, default)

        if current_config is default:
            break
    
    if current_config is NO_DEFAULT:
        raise KeyError(f"Config file has no element '{path}'")

    return current_config
