# encoding: utf-8

# Copyright (c) IPython-extensions Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import division, print_function, absolute_import

__all__ = ["demo"]

import inspect
from textwrap import dedent
import re
import sys

try:
    #py3
    from base64 import decodebytes
except ImportError:
    # py2
    from base64 import decodestring as decodebytes


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = (str,),
    text_type = str
    binary_type = bytes
    long = int
else:
    string_types = (str, unicode),
    text_type = unicode
    binary_type = str

def demo(content, frontend=None):
    """Run a demo or view all available demos.
    Parameters
    ----------
    content : whatever content should be displayed as a demo source
        Examples include a passed in function or module or a path on github in the form
        ``"<gh_project>/path/to/demo.py"`` (where project is a known project which provides demos
        on github)
    frontend : Frontend instace (optional, default is NotebookFrontend)
        A frontend, which should display the demo (currently only used for testing purpose)

    """
    if frontend is None:
        frontend = NotebookFrontend()
    elif frontend == "ipython":
        frontend = IPythonFrontend()

    if content == "STOP":
        frontend.abbort()
        return

    backend = None
    for be in [GithubURLBackend, PythonCodeBackend]:
        cand = be()
        if cand.can_handle(content):
            backend = cand
    try:
        type, content = backend.get(content)
    except Exception as e:
        print(e.args)
        return

    if type == "toc":
        name, toc = content
        frontend.display_toc(name, toc)
    elif type == "cells":
        frontend.insert_demo(content)


class Backend(object):
    def can_handle(self, content):
        """
        Parameters
        ----------
        content : Whatever input demo got
           The content which should be used as the demo source

        Returns
        -------
        Bool : whether or not this backend can handle the content
        """
        raise NotImplementedError

    def get(self, content):
        """Gets content from the backend.

        Parameters
        ----------
        content : Whatever input demo got and we can handle
           The content which should be used as the demo source

        Returns
        -------
        (type, content) : the type and real content for this content
            ``type`` is one of "toc" or "cells". ``content`` is a list of tuples ``(name,
            description)`` which should be displayed as available demos (if ``type=="toc"``) or
            a a list of ``cells`` which should be displayed.
        """
        raise NotImplementedError

class PythonCodeBackend(Backend):

    def can_handle(self, content):
        if inspect.ismodule(content) or inspect.isfunction(content):
            return True
        return False

    def get(self, content):
        if inspect.ismodule(content):
            if hasattr(content, "__demos__"):
                name = content.__name__
                demos = content.__demos__
                toc =  [(d.__name__, d.__doc__) for d in demos]
                return "toc", (name, toc)
            else:
                msg = "The module {0} has no demos available."
                raise Exception(msg.format(content.__name__))
        elif not inspect.isfunction(content):
            msg = "Not a module or a function: {0}"
            raise Exception(msg.format(content))
        else:
            # we have a function...
            # TODO: make sure that the function takes no argument

            source = inspect.getsource(content)
            return "cells", _function_source_to_cells(source)

_URLS_GITHUBURLBACKEND = {
    "matplotlib": 'https://api.github.com/repos/matplotlib/matplotlib/contents'
                  '/examples/{0}'
}

_RE_GITHUBURLBACKEND = re.compile(r"^<gh_.*>.*")
class GithubURLBackend(Backend):

    def can_handle(self, content):
        if isinstance(content, string_types):
            if _RE_GITHUBURLBACKEND.search(content) is not None:
                return True
        return False

    def get(self, content):
        import requests
        typ = "cells" if content.endswith(".py") else "toc"
        # add a trailing slash
        if content[-1:] != "/":
            content = content + "/"
        name = content
        content = content.split("/")
        # get the base source for the demo, which is the first element minus the <gh_.*> stuff
        demo_source = content[0][4:-1]
        if demo_source not in _URLS_GITHUBURLBACKEND:
            raise Exception("Unknown github demo source: {0}".format(demo_source))
        base_url = _URLS_GITHUBURLBACKEND[demo_source]
        path = "/".join(content[1:])
        headers = {"accept": "application/vnd.github.v3.json"}
        url = base_url.format(path)
        #print(url)
        r = requests.get(url, headers=headers)
        ret = r.json()
        # unauthenticated requests have a ratelimit...
        if 'message' in ret:
            raise Exception(ret['message'])
        if typ == "cells":
            content = ret["content"]
            content = decodebytes(content.encode())
            content = content.decode()
            # Todo: split into cells?
            return typ, [{"source": content, "cell_type":"code"}]
        elif typ == "toc":
            #ret = ret[0]
            #print(ret)
            files = [item for item in ret if item['type'] == 'file']
            dirs = [item for item in ret if item['type'] == 'dir']
            demo_names = [name+item["name"] for item in files]
            demos = [(name, "") for name in demo_names if name.endswith(".py")]
            dir_names = [name+item["name"] for item in dirs]
            more_demos = [(name, "[directory}") for name in dir_names]
            return typ, (name, demos + more_demos)
        raise Exception("This should not happen...")

class Frontend(object):

    def _publish(self):
        """Publishes the content of the demo to the frontend"""
        raise NotImplementedError

    def _build(self, cells):
        """Builds the to be published content from the cells"""
        raise NotImplementedError

    def abbort(self):
        """Stops a already running demo, if not already published in full"""
        raise NotImplementedError

    def insert_demo(self, cells):
        self._build(cells)
        self._publish()

    def display_toc(self, name, toc):
        msg = """\
        "{0}" has the following demo(s) available:

        {1}
        """
        msg = dedent(msg)
        demos = ["* {0}: {1}".format(d[0], d[1]) for d in toc]
        print(msg.format(name, "\n".join(demos) ))


class IPythonFrontend(Frontend):

    # This is ententional a class atribute to also work as a sentinel if another demo is already
    # running
    _buffer = []

    def __init__(self):
        if self._buffer:
            raise Exception("Already in a running demo, abort with 'demo(\"STOP\")'")
        try:
            self.ip = get_ipython()
            self._orig_run_cell = self.ip.run_cell
        except:
            raise Exception("Not running in a IPython environment")

    def abbort(self):
        """Stops a already running demo, if not already published in full"""
        if not self._buffer:
            print("Not in a demo, nothing to stop!")
            return
        while self._buffer:
            self._buffer.pop(0)
        # deinstall the wrapper
        self.ip.run_cell = self._orig_run_cell
        print("Demo stopped!")

    def _publish(self):
        """Publishes the content of the demo to the frontend"""
        that = self
        def run_cell_wrapper(*args, **kwargs):
            if not that._buffer:
                # Failsave if the wrapper wasn't deinstalled
                that.ip.run_cell = that._orig_run_cell
            # run current code
            that._orig_run_cell(*args, **kwargs)
            # set next input to the next code in buffer
            if that._buffer:
                code = that._buffer.pop(0)
                that.ip.set_next_input(code, replace=False)
            else:
                # deinstall the wrapper if the buffer is empty
                that.ip.run_cell = that._orig_run_cell


        self.ip.run_cell = run_cell_wrapper
        code = self._buffer.pop(0)
        self.ip.set_next_input(code, replace=False)


    def _build(self, cells):
        """In this case just fills a buffer"""
        md_buffer = None
        for cell in cells:
            source = cell['source'].strip()
            if cell['cell_type'] == 'markdown':
                lines = source.split("\n")
                lines = ["# " + line for line in lines]
                #lines.append("pass # do not remove") # to make even comment only cells to run
                # something
                commented = "\n".join(lines)
                md_buffer = commented
            elif cell['cell_type'] == 'code':
                if md_buffer is not None:
                    # cell magics need to be at the start of a cell
                    if source[0:2] == "%%":
                        self._buffer.append(md_buffer)
                    else:
                        source = md_buffer + "\n" + source
                    md_buffer = None
                self._buffer.append(source)
        if md_buffer is not None:
            self._buffer.append(md_buffer)




# Adapted from https://github.com/jupyter-incubator/contentmanagement/blob/master/urth/cms/inject.py
class NotebookFrontend(Frontend):

    def __init__(self):
        self._js = []

    def abbort(self):
        """Stops a already running demo, if not already published in full"""
        print("Full demo already visible, please just delete all cells")

    def _publish(self):
        """Publishes the content of the demo to the frontend"""
        from IPython.display import display, Javascript
        display(Javascript("\n".join(self._js)))

    def _build(self, cells):
        '''
        Creates a series of JS commands to inject code and markdown cells from
        the passed notebook structure into the existing notebook sans output.
        '''
        import json
        js = self._js
        js += ['var i = IPython.notebook.get_selected_index();']
        i = 0
        for cell in cells:
            if cell['cell_type'] == 'markdown':
                js.append("var cell = IPython.notebook.insert_cell_below('markdown', i+{});".format(i))
                escaped_source = json.dumps(cell['source'].strip()).strip('"')
                js.append('cell.set_text("{}");'.format(escaped_source))
                js.append('cell.rendered = false; cell.render();')
                i += 1
            elif cell['cell_type'] == 'code':
                js.append("var cell = IPython.notebook.insert_cell_below('code', i+{});".format(i))
                escaped_input = json.dumps(cell['source'].strip()).strip('"')
                js.append('cell.set_text("{}");'.format(escaped_input))
                i += 1

        js.append('var self = this; setTimeout(function() { self.clear_output(); }, 0);')

###################################################################################################
#
# Helper functions
#
###################################################################################################

_RE_MAGICS = re.compile(r"^#%")
_RE_MD = re.compile(r"^# ")

def _function_source_to_cells(source):
    lines = source.split("\n")
    # remove the function declaration and the docstring
    lines = lines[2:]
    source = "\n".join(lines)
    # remove whitespace as needed ans split again...
    source = dedent(source)

    lines = source.split("\n")

    # convert commented magics to life magics
    lines = [_RE_MAGICS.sub("%", line) for line in lines]
    # identify markdown lines
    lines = [("markdown" if _RE_MD.search(line) else "code", _RE_MD.sub("", line))
                   for line in lines]
    # ... and convert to "cell" contents
    cells = []
    state = None
    buffer = []
    for typ, line in lines + [("END", "")]:
        if buffer and typ != state:
            cell = {
                "source": "\n".join(buffer),
                "cell_type": state
                     }
            cells.append(cell)
            buffer = []
        state = typ
        buffer.append(line)
    # Intentionally leave the buffer full with the last "END" state
    return cells


###################################################################################################
#
# Now starts the demo of a demo :-)
#
###################################################################################################

def demo_example():
    """An example how to write a demo."""
    # ## Comments
    # Comments are interpreted as markdown syntax, removing the initial `# `.
    # If a comment starts only as `#` it is interpreted as a comment, which will
    # end up together with the code.
    #change your name:
    name = "Jan"
    print("Hello {0}!".format(name))
    # ## Magics
    # Using magics would result in not compiling code, so magics have to be commented out.
    # The demo will remove the comment and insert it into the cell as code.
    #%%time
    _sum = 0
    for x in range(10000):
        _sum += x
    # Print the sum:
    print(_sum)

__demos__ = [demo_example]