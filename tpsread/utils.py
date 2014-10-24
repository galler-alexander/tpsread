from warnings import warn


def check_value(name, value, check):
    if value != check:
        # TODO check translate
        warn('Value of parameter "{param_name}": "{param_value}" does not coincide with a typical "{param_check}"'
             .format(param_name=name, param_value=value, param_check=check), RuntimeWarning, 2)


if __name__ == '__main__':
    check_value('test_param', 0, 1)
