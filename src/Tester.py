""" functions used to run tests """

from functools import partial
from copy import deepcopy
from stopit import ThreadingTimeout
import stopit
from tabulate import tabulate

# constants
SEPERATOR = '#' * 15
TIMEOUT_SEC = 5
INFINITE_LOOP_STR = 'Function call did not return in < 5sec, likely an infinite loop\n'
FUNC_TEST_HEADER = SEPERATOR + ' function: %s, score: %d/%d' + SEPERATOR + '\n'
RUN_TIME_ERR_STR = 'An error ocurred during excuting of your function\n'
LOAD_TIME_ERR_STR = 'An error occured when loading your function for grading\n'


def run_with_timeout(func):
    """
    execute a fully curried function under prescribed time out
    :param func: fully curried partial instance
    :return: return value of the function, or none if it times out
    """
    with ThreadingTimeout(TIMEOUT_SEC):
        exc_str = None
        return_val = None
        time_out = False
        # noinspection PyBroadException
        try:
            return_val = func()
        except stopit.utils.TimeoutException:
            time_out = True
        except Exception:
            exc_str = RUN_TIME_ERR_STR
    return time_out, return_val, exc_str


# test a single arg_set for given function, return test result instance
def test_one_arg_set(arg_set, stf_func, sol_func):
    """
    execute a single test case
    :param arg_set: list of arguments
    :param stf_func: function from student submission
    :param sol_func: function from solution file
    :return: an ArgSetTestResult instance
    """
    for arg in arg_set:
        stf_func = partial(stf_func, deepcopy(arg))
        sol_func = partial(sol_func, deepcopy(arg))
    is_timeout, return_val, exc_str = run_with_timeout(stf_func)
    answer_key = sol_func()
    arg_set_partial = partial(ArgSetTestResult, arg_set, answer_key)
    if is_timeout:
        return arg_set_partial(None, INFINITE_LOOP_STR)
    elif exc_str:
        return arg_set_partial(None, exc_str)
    else:
        return arg_set_partial(return_val, None)


def test_func(func, stf, sol_name):
    """
    test a given function for all test cases
    :param func: a Func instance
    :param stf: a StudentFile instance
    :param sol_name: path to solution file
    """
    sol_func = getattr(__import__(sol_name), func.name)
    # noinspection PyBroadException
    try:
        sft_func = getattr(__import__(stf.file_xext()), func.name)
    except Exception:
        func_result = FuncTestResult(func.name, func.score, True)
        stf.function_test_results.append(func_result)
        return

    func_result = FuncTestResult(func.name, func.score, False)
    stf.function_test_results.append(func_result)
    for arg_set in func.arg_sets:  # set up function calls
        set_result = test_one_arg_set(arg_set, sft_func, sol_func)
        func_result.add_set_result(set_result)


class FuncTestResult:
    """
    Meta information about testing of this function
    """
    def __init__(self, function_name, score, exc):
        self.function_name = function_name
        self.score = score
        self.arg_sets_res = []
        self.exc = exc

    def add_set_result(self, result):
        """
        add a new ArgSetTestResult instance
        :param result: ArgSetTestResult instance to be added
        """
        self.arg_sets_res.append(result)

    def calc_score(self):
        """
        calculate the score should be given for all test cases of this function
        all or nothing
        :return: the deserved score
        """
        if self.exc:
            return 0
        for set_result in self.arg_sets_res:
            if not set_result.is_correct:
                return 0
        return self.score

    def __str__(self):

        if self.exc:
            score_recieved = 0
            body = LOAD_TIME_ERR_STR
        else:
            score_recieved = self.calc_score()
            num_tests = str(len(self.arg_sets_res))
            body = num_tests + ' cases were tested\n'
        header = FUNC_TEST_HEADER % (self.function_name, score_recieved, self.score)
        res_str = []
        for i in range(0, len(self.arg_sets_res)):
            res_str.append(f'case {i}\n{str(self.arg_sets_res[i])}')
        return header + body + '\n\n'.join(res_str)


class ArgSetTestResult:
    """
    Testing result of a single set of input arguments
    """
    def __init__(self, inputs, expected, actual, exception_str):
        self.inputs = inputs
        self.expected = expected
        self.actual = actual
        self.exception_str = exception_str
        self.is_correct = expected == actual
    
    # to return a string representation of this test result
    def __str__(self):
        expected_val = str(self.expected)
        if type(self.expected) == str:
            expected_val = '\"' + expected_val + '\"'
        actual_val = str(self.actual)
        if type(self.actual) == str:
            actual_val = '\"' + actual_val + '\"'
        res = "PASSED"
        if not self.is_correct:
            res = "FAILED"
        grid = [
            [res, 'value returned', 'type returned'],
            ['expected', expected_val, str(type(self.expected))],
            ['actual', actual_val, str(type(self.actual))]
        ]
        in_str = f'inputs: ({str(self.inputs)[1:-1]})\n'
        return_str = in_str + tabulate(grid, tablefmt='grid') + '\n'
        if self.exception_str is not None:
            return_str += self.exception_str
        return return_str


def grade_section(sol_fname, funcs, section):
    """
    grade all student files of a section
    :param sol_fname: path to solution file
    :param funcs: functions to be tested
    :param section: a section instance to be graded
    """
    for stf in section.student_files:
        for func in funcs:
            test_func(func, stf, sol_fname)


class Func:
    """
    Specs of a single function
    """
    def __init__(self, name, arg_sets, score):
        self.name = name
        self.arg_sets = arg_sets
        self.score = score
        self.testResults = []
