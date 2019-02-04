# Server Specific Configurations
server = {
    'port': '6000',
    'host': '127.0.0.1'
}

# Pecan Application Configurations
app = {
    'root': 'pseudonym.controllers.root.RootController',
    'modules': ['pseudonym'],
    'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/pseudonym/templates',
    'debug': False
}

database = {
    'url': 'mongodb://localhost:27017/'
}

logging = {
    'root': {'level': 'INFO', 'handlers': ['console']},
    'loggers': {
        'pseudonym': {'level': 'DEBUG', 'handlers': ['console'], 'propagate': False},
        'pecan': {'level': 'DEBUG', 'handlers': ['console'], 'propagate': False},
        'py.warnings': {'handlers': ['console']},
        '__force_dict__': True
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'color'
        }
    },
    'formatters': {
        'simple': {
            'format': ('%(asctime)s %(levelname)-5.5s [%(name)s]'
                       '[%(threadName)s] %(message)s')
        },
        'color': {
            '()': 'pecan.log.ColorFormatter',
            'format': ('%(asctime)s [%(padded_color_levelname)s] [%(name)s]'
                       '[%(threadName)s] %(message)s'),
        '__force_dict__': True
        }
    }
}
