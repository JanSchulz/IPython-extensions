.. currentmodule:: ipyext
.. _demo_mode:

*************
Demo mode
*************

.. currentmodule:: ipyext.demo

.. ipython:: python
    
    from ipyext.demo import demo
    import ipyext.demo
    demo(ipyext.demo)
    demo("<gh_matplotlib>/statistics/")
    # stops an already running demo
    demo("STOP")


.. autosummary::
   :toctree: generated/

    demo

