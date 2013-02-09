#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path
import re
import sys

import pep8
from pep8 import Checker, StyleGuide, BaseReport, StandardReport, readlines

SELFTEST_REGEX = re.compile(r'\b(Okay|[EW]\d{3}):\s(.*)')


class TestReport(StandardReport):
    """Collect the results for the tests."""

    def __init__(self, options):
        options.benchmark_keys += ['test cases', 'failed tests']
        super(TestReport, self).__init__(options)
        self._verbose = options.verbose

    def get_file_results(self):
        # Check if the expected errors were found
        label = '%s:%s:1' % (self.filename, self.line_offset)
        codes = sorted(self.expected)
        for code in codes:
            if not self.counters.get(code):
                self.file_errors += 1
                self.total_errors += 1
                print('%s: error %s not found' % (label, code))
        if self._verbose and not self.file_errors:
            print('%s: passed (%s)' %
                  (label, ' '.join(codes) or 'Okay'))
        self.counters['test cases'] += 1
        if self.file_errors:
            self.counters['failed tests'] += 1
        # Reset counters
        for key in set(self.counters) - set(self._benchmark_keys):
            del self.counters[key]
        self.messages = {}
        return self.file_errors

    def print_results(self):
        results = ("%(physical lines)d lines tested: %(files)d files, "
                   "%(test cases)d test cases%%s." % self.counters)
        if self.total_errors:
            print(results % ", %s failures" % self.total_errors)
        else:
            print(results % "")
        print("Test failed." if self.total_errors else "Test passed.")


def init_tests(pep8style):
    """
    Initialize testing framework.

    A test file can provide many tests.  Each test starts with a
    declaration.  This declaration is a single line starting with '#:'.
    It declares codes of expected failures, separated by spaces or 'Okay'
    if no failure is expected.
    If the file does not contain such declaration, it should pass all
    tests.  If the declaration is empty, following lines are not checked,
    until next declaration.

    Examples:

     * Only E224 and W701 are expected:         #: E224 W701
     * Following example is conform:            #: Okay
     * Don't check these lines:                 #:
    """
    report = pep8style.init_report(TestReport)
    runner = pep8style.input_file

    def run_tests(filename):
        """Run all the tests from a file."""
        lines = readlines(filename) + ['#:\n']
        line_offset = 0
        codes = ['Okay']
        testcase = []
        count_files = report.counters['files']
        for index, line in enumerate(lines):
            if not line.startswith('#:'):
                if codes:
                    # Collect the lines of the test case
                    testcase.append(line)
                continue
            if codes and index:
                codes = [c for c in codes if c != 'Okay']
                # Run the checker
                runner(filename, testcase, expected=codes,
                       line_offset=line_offset)
            # output the real line numbers
            line_offset = index + 1
            # configure the expected errors
            codes = line.split()[1:]
            # empty the test case buffer
            del testcase[:]
        report.counters['files'] = count_files + 1
        return report.counters['failed tests']

    pep8style.runner = run_tests


def selftest(options):
    """
    Test all check functions with test cases in docstrings.
    """
    count_failed = count_all = 0
    report = BaseReport(options)
    counters = report.counters
    checks = options.physical_checks + options.logical_checks
    for name, check, argument_names in checks:
        for line in check.__doc__.splitlines():
            line = line.lstrip()
            match = SELFTEST_REGEX.match(line)
            if match is None:
                continue
            code, source = match.groups()
            lines = [part.replace(r'\t', '\t') + '\n'
                     for part in source.split(r'\n')]
            checker = Checker(lines=lines, options=options, report=report)
            checker.check_all()
            error = None
            if code == 'Okay':
                if len(counters) > len(options.benchmark_keys):
                    codes = [key for key in counters
                             if key not in options.benchmark_keys]
                    error = "incorrectly found %s" % ', '.join(codes)
            elif not counters.get(code):
                error = "failed to find %s" % code
            # Keep showing errors for multiple tests
            for key in set(counters) - set(options.benchmark_keys):
                del counters[key]
            report.messages = {}
            count_all += 1
            if not error:
                if options.verbose:
                    print("%s: %s" % (code, source))
            else:
                count_failed += 1
                print("%s: %s:" % (pep8.__file__, error))
                for line in checker.lines:
                    print(line.rstrip())
    return count_failed, count_all


def run_tests(style, doctest=True, testsuite=False):
    options = style.options
    if doctest:
        import doctest
        fail_d, done_d = doctest.testmod(report=False, verbose=options.verbose)
        fail_s, done_s = selftest(options)
        count_failed = fail_s + fail_d
        if not options.quiet:
            count_passed = done_d + done_s - count_failed
            print("%d passed and %d failed." % (count_passed, count_failed))
            print("Test failed." if count_failed else "Test passed.")
        if count_failed:
            sys.exit(1)
    if testsuite:
        init_tests(style)
    return style.check_files()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        sys.exit(pep8._main())
    pep8style = StyleGuide(paths=[os.path.dirname(__file__)], ignore=None)
    report = run_tests(pep8style, doctest=True, testsuite=True)
    report.print_results()
    sys.exit(1 if report.total_errors else 0)
