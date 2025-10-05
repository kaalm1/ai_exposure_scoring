import logging

for logger_name in ['sqlalchemy', 'sqlalchemy.engine', 'sqlalchemy.pool',
                     'sqlalchemy.dialects', 'sqlalchemy.orm']:
    logging.getLogger(logger_name).setLevel(logging.ERROR)
    logging.getLogger(logger_name).propagate = False
    logging.getLogger(logger_name).disabled = True

# Method 1: Mute specific libraries
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)