.. currentmodule:: ipyext
.. _demo_mode:

*************
Demo mode
*************

.. currentmodule:: ipyext.demo

As a User
---------

There are currently two possible sources of demos:

* plain (self contained) functions included in modules
  of libraries you use.
* the matplotlib examples in their github repository

``demo(...)`` has two modes:

* for a imported module or a directory on github, it will list the available demos.
* for a function or a file on github, it will show the demo.

Example:

.. ipython:: python

    from ipyext.demo import demo
    import ipyext.demo
    demo(ipyext.demo) # lists all demos
    demo(ipyext.demo.demo_example) # runs the demo_example
    demo("STOP") # stops an already running demo
    demo("<gh_matplotlib>/statistics/") # lists demos from matplotlibs' examples


Hiere is the API documentation of ``demo()``

.. autosummary::
   :toctree: generated/

    demo

As a developer
--------------

You can create demos by adding a new module which should contain two things:

* One or more *self contained functions* which take *no arguments*. The
  functions can have two types of *comments*: ``"# "`` (fence + space) are
  interpreted as markdown (e.g. write ``"# # headline"``) and result in
  markdown cells in the notebook and normal comments in the console.
  Comments without a space are interpreted as code comments and added
  directly to the following code input. You can add a *one line docstring*
  which will be shown as description of the demo in the list of available
  demos. Using *IPython magic methods* are also possible but must be
  commented.
* A ``__demos__`` field in the module which *lists all demo functions* (direct
  reference, not strings like in ``__all__``!).

Example:

.. code-block:: python

    def demo_example():
        """An example how to write a demo."""
        # ## Comments
        # Comments are interpreted as markdown syntax, removing the
        # initial `# `. If a comment starts only with `#`, it is interpreted
        # as a code comment, which will end up together with the code.
        #change your name:
        name = "Jan"
        print("Hello {0}!".format(name))
        # ## Magics
        # Using magics would result in not compiling code, so magics
        # have to be commented out. The demo will remove the comment
        # and insert it into the cell as code.
        #%%time
        _sum = 0
        for x in range(10000):
            _sum += x
        # Print the sum:
        print(_sum)

    # This lets the `demo(ipyext.demo)` find only the `demo_example`.
    # Only modues with that variable will display an overview of
    # the available demos.
    __demos__ = [demo_example]
