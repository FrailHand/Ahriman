def warning(*print_args, title=""):
    print('\033[93m\033[1mWarning\033[0m\033[93m {} : \033[0m'.format(title), *print_args)


def error(*print_args, title=""):
    print('\033[91m\033[1mError\033[0m\033[91m {} : \033[0m'.format(title), *print_args)


def info(*print_args, title=""):
    print('\033[94m\033[1mInfo\033[0m\033[94m {} : \033[0m'.format(title), *print_args)


def confirm(*print_args, title=""):
    print('\033[32m\033[1mSuccess\033[0m\033[32m {} : \033[0m'.format(title), *print_args)
