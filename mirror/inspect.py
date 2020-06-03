import inspect
import os

def current_module_name():
    calling_globals = inspect.stack()[1][0].f_globals
    
    if calling_globals['__name__'] != '__main__':
        return calling_globals['__name__']

    fqmn = ""
    if calling_globals['__package__']:
        fqmn += calling_globals['__package__'] + "."
    
    fqmn += os.path.basename(calling_globals['__file__']).rsplit('.', 1)[0]
    return fqmn
