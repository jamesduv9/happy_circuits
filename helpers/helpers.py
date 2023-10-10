import operator

comparison_functions = {
    "le": operator.le,
    "lt": operator.lt,
    "ge": operator.ge,
    "gt": operator.gt,
    "eq": operator.eq
}

def compare_values(value:int, oper:str) -> bool:
    """
    Compares the given value against the condition defined in 'oper'.
    """
    oper_list = oper.split(" ")
    
    # Check the operation structure
    if len(oper_list) != 2:
        raise ValueError(f"Failed to understand the provided operation {oper}")

    # Fetch the comparison function directly using the shorthand string
    comparison_func = comparison_functions.get(oper_list[0])
    if not comparison_func:
        raise ValueError(f"Unknown operator: {oper_list[0]}")

    # Convert the second part of the operation to an integer
    try:
        real_int = int(oper_list[1])
    except ValueError:
        raise ValueError(f"Failed to convert the second item in the operation to an integer. Malformed operation {oper}")

    # Perform the actual comparison
    return comparison_func(value, real_int)


def split_load(loadstr):
    """
    Extremely basic function that splits the load string and returns the first value. 
    ex.  split_load("1/255") | returns "1"
    """
    loadstr = loadstr.split("/")
    if len(loadstr) < 2:
        raise ValueError(f"Malformed load input, this doesnt look like load value - {loadstr}")
    try:
        int(loadstr[0])
        int(loadstr[1])
    except ValueError:
        raise ValueError(f"One of these values could not be turned into an integer {loadstr}")
    if int(loadstr[1]) != 255:
        raise ValueError(f"This doesn't look like a load string, the second value should be 255 {loadstr}")
    return int(loadstr[0])


def split_subintf(subintf):
    """
    Extremely basic function that splits a subinterface and returns it's parent interface
    ex.  split_load("GigabitEthernet0/1.100") | returns "GigabitEthernet0/1"
    """
    subintf = subintf.split(".")
    if len(subintf) < 2:
        raise ValueError(f"Malformed subinterface - {subintf}")
    return subintf[0]

def milliseconds_to_days(milliseconds):
    seconds = milliseconds / 1000  # Convert milliseconds to seconds
    minutes = seconds / 60         # Convert seconds to minutes
    hours = minutes / 60           # Convert minutes to hours
    days = hours / 24              # Convert hours to days
    
    return days