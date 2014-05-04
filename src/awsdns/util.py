"""
AWSDNS - DNS for EC2 instances in Amazon Web Services

Utility functions
"""
import logging 

def logging_constant(const):
    """
    Return the logging constant for a given log level constant:
    
    CRITICAL 	50
    ERROR 	40
    WARNING 	30
    INFO 	20
    DEBUG 	10
    NOTSET 	0
    
    TODO: would it be safe to hard code these values instead of doing a dynamic
          lookup?
    """
    try:
        value = getattr(logging, const.upper())
        
        # make sure it's not some other object :)
        if not isinstance(value, int):
            raise AttributeError
            
        return value
    except AttributeError:
        raise ValueError, "'%s' is not a valid log level" % (const)
