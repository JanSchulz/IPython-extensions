# -*- coding: utf-8 -*-
"""Tests for the demo mode.
"""

from __future__ import absolute_import

import nose.tools as nt
import mock

from IPython.testing import tools as tt

from ipyext.demo import demo, Frontend, GithubURLBackend
import ipyext.demo

class TestFrontent(Frontend):

    def __init__(self, expected):
        self.buffer = []
        self.expected = expected

    def _publish(self):
        """Publishes the content of the demo to the frontend"""
        nt.maxDiff = None
        nt.assert_list_equal(self.buffer, self.expected)

    def _build(self, cells):
        """Builds the to be published content from the cells"""
        for cell in cells:
            self.buffer.append(cell['cell_type'])
            self.buffer.append(cell['source'])

    def is_running(self):
        if self.buffer:
            return True
        return False


def test_github_backend():
    # this only works if we have access to the internet...
    backend = GithubURLBackend()
    typ, content = backend.get("<gh_matplotlib>")
    nt.assert_equal(typ, "toc")
    typ, content = backend.get("<gh_matplotlib>/style_sheets/plot_grayscale.py")
    nt.assert_equal(typ, "cells")
    # no full test of the content as I don't want to rely on github and matplotlib for this...

    with tt.AssertPrints("Unknown github demo source"):
        demo("<gh_not_xxx_existing>")


def test_python_backend():

    with tt.AssertPrints("has no demos available."):
        demo(nt)

    with tt.AssertPrints("has the following demo(s) available:"):
        demo(ipyext.demo)

    with tt.AssertPrints("demo_example"):
        demo(ipyext.demo)

    exp = [
        "markdown",
        "\n".join([
            "## Comments",
            "Comments are interpreted as markdown syntax, removing the",
            "initial `# `. If a comment starts only with `#`, it is interpreted",
            "as a code comment, which will end up together with the code."
            ]),
        "code",
        "\n".join([
            '#change your name:',
            'name = "Jan"',
            'print("Hello {0}!".format(name))'
            ]),
        "markdown",
        "\n".join([
            "## Magics",
            "Using magics would result in not compiling code, so magics",
            "have to be commented out. The demo will remove the comment",
            "and insert it into the cell as code."
            ]),
        "code",
        "\n".join([
            "%%time",
            "_sum = 0",
            "for x in range(10000):",
            "    _sum += x"
            ]),
        "markdown",
        "Print the sum:",
        "code",
        "print(_sum)\n"
        ]

    fe = TestFrontent(exp)

    demo(ipyext.demo.demo_example, frontend=fe)


def test_wrong_frontend():
    with tt.AssertPrints("Not a valid frontend"):
        demo(nt, frontend="Not_Existing")


@mock.patch('IPython.display.display')
def test_notebook_frontend(mock_display):
    from IPython.core.display import Javascript
    ip = get_ipython()
    ip.run_cell("from ipyext.demo import demo\nimport ipyext.demo")
    ip.run_cell("demo(ipyext.demo.demo_example)")
    nt.assert_true(mock_display.called)
    nt.assert_equal(mock_display.call_count, 1)
    # call_args = ((Javascript(...),),)
    nt.assert_is_instance(mock_display.call_args[0][0], Javascript)
    nt.assert_true("insert_cell_below" in mock_display.call_args[0][0]._repr_javascript_())
    with tt.AssertPrints("No demo running... Nothing to do."):
        ip.run_cell("demo('STOP')")


@mock.patch('IPython.core.interactiveshell.InteractiveShell.set_next_input')
def test_ipython_frontend(mock_set_next_input):
    from IPython.core.display import Javascript
    ip = get_ipython()
    ip.run_cell("from ipyext.demo import demo\nimport ipyext.demo")
    with tt.AssertPrints("Starting demo..."):
        ip.run_cell("demo(ipyext.demo.demo_example, frontend='ipython')")
    nt.assert_true("IPythonFrontend._post_run_cell" in repr(ip.events.callbacks["post_run_cell"]))
    print(mock_set_next_input.call_args)
    nt.assert_true(mock_set_next_input.called)
    nt.assert_equal(mock_set_next_input.call_count, 1)
    # call_args = (("<firstcell...>,),replace=False)
    nt.assert_true("Comments are interpreted as markdown syntax" in mock_set_next_input.call_args[0][0])
    ip.run_cell("pass")
    nt.assert_true("Using magics would result" in mock_set_next_input.call_args[0][0])
    with tt.AssertPrints("Demo stopped!"):
        ip.run_cell("demo('STOP')")
    nt.assert_false("IPythonFrontend._post_run_cell" in repr(ip.events.callbacks["post_run_cell"]))


if __name__ == '__main__':
    import nose

    nose.runmodule(argv=[__file__, '-vs', '-x'],# '--pdb', '--pdb-failure'],
                   # '--with-coverage', '--cover-package=pandas.core'],
                   exit=False)
