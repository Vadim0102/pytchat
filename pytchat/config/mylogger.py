from logging import NullHandler, getLogger, StreamHandler, FileHandler
import logging
from datetime import datetime


def get_logger(modname, loglevel=logging.DEBUG):
    logger = getLogger(modname)
    logger.propagate = False

    if loglevel is None:
        if not any(isinstance(handler, NullHandler) for handler in logger.handlers):
            logger.addHandler(NullHandler())
        return logger

    logger.setLevel(loglevel)
    my_formatter = MyFormatter()

    # create handler1 for showing info
    if not any(isinstance(handler, StreamHandler) and not isinstance(handler, FileHandler)
               for handler in logger.handlers):
        handler1 = StreamHandler()
        handler1.setFormatter(my_formatter)
        handler1.setLevel(loglevel)
        logger.addHandler(handler1)

    # create handler2 for recording log file (debug mode should record everything)
    if loglevel <= logging.DEBUG and not any(isinstance(handler, FileHandler) for handler in logger.handlers):
        handler2 = FileHandler(filename="log.txt", encoding='utf-8')
        handler2.setLevel(loglevel)
        handler2.setFormatter(my_formatter)
        logger.addHandler(handler2)
    return logger


class MyFormatter(logging.Formatter):
    def format(self, record):
        timestamp = (
            datetime.fromtimestamp(record.created)).strftime("%m-%d %H:%M:%S")
        module = (record.module).ljust(15)
        funcname = (record.funcName).ljust(18)
        lineno = str(record.lineno).rjust(4)
        message = record.getMessage()

        return timestamp + '| ' + module + ' { ' + funcname + ':' + lineno + '} - ' + message
