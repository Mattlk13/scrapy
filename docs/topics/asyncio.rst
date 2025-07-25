.. _using-asyncio:

=======
asyncio
=======

.. versionadded:: 2.0

Scrapy has partial support for :mod:`asyncio`. After you :ref:`install the
asyncio reactor <install-asyncio>`, you may use :mod:`asyncio` and
:mod:`asyncio`-powered libraries in any :doc:`coroutine <coroutines>`.


.. _install-asyncio:

Installing the asyncio reactor
==============================

To enable :mod:`asyncio` support, your :setting:`TWISTED_REACTOR` setting needs
to be set to ``'twisted.internet.asyncioreactor.AsyncioSelectorReactor'``,
which is the default value.

If you are using :class:`~scrapy.crawler.AsyncCrawlerRunner` or
:class:`~scrapy.crawler.CrawlerRunner`, you also need to
install the :class:`~twisted.internet.asyncioreactor.AsyncioSelectorReactor`
reactor manually. You can do that using
:func:`~scrapy.utils.reactor.install_reactor`:

.. skip: next
.. code-block:: python

    install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")


.. _asyncio-preinstalled-reactor:

Handling a pre-installed reactor
================================

``twisted.internet.reactor`` and some other Twisted imports install the default
Twisted reactor as a side effect. Once a Twisted reactor is installed, it is
not possible to switch to a different reactor at run time.

If you :ref:`configure the asyncio Twisted reactor <install-asyncio>` and, at
run time, Scrapy complains that a different reactor is already installed,
chances are you have some such imports in your code.

You can usually fix the issue by moving those offending module-level Twisted
imports to the method or function definitions where they are used. For example,
if you have something like:

.. skip: next
.. code-block:: python

    from twisted.internet import reactor


    def my_function():
        reactor.callLater(...)

Switch to something like:

.. code-block:: python

    def my_function():
        from twisted.internet import reactor

        reactor.callLater(...)

Alternatively, you can try to :ref:`manually install the asyncio reactor
<install-asyncio>`, with :func:`~scrapy.utils.reactor.install_reactor`, before
those imports happen.


.. _asyncio-await-dfd:

Integrating Deferred code and asyncio code
==========================================

Coroutine functions can await on Deferreds by wrapping them into
:class:`asyncio.Future` objects. Scrapy provides two helpers for this:

.. autofunction:: scrapy.utils.defer.deferred_to_future
.. autofunction:: scrapy.utils.defer.maybe_deferred_to_future

.. tip:: If you don't need to support reactors other than the default
         :class:`~twisted.internet.asyncioreactor.AsyncioSelectorReactor`, you
         can use :func:`~scrapy.utils.defer.deferred_to_future`, otherwise you
         should use :func:`~scrapy.utils.defer.maybe_deferred_to_future`.

.. tip:: If you need to use these functions in code that aims to be compatible
         with lower versions of Scrapy that do not provide these functions,
         down to Scrapy 2.0 (earlier versions do not support
         :mod:`asyncio`), you can copy the implementation of these functions
         into your own code.

Coroutines and futures can be wrapped into Deferreds (for example, when a
Scrapy API requires passing a Deferred to it) using the following helpers:

.. autofunction:: scrapy.utils.defer.deferred_from_coro
.. autofunction:: scrapy.utils.defer.deferred_f_from_coro_f


.. _enforce-asyncio-requirement:

Enforcing asyncio as a requirement
==================================

If you are writing a :ref:`component <topics-components>` that requires asyncio
to work, use :func:`scrapy.utils.asyncio.is_asyncio_available` to
:ref:`enforce it as a requirement <enforce-component-requirements>`. For
example:

.. code-block:: python

    from scrapy.utils.asyncio import is_asyncio_available


    class MyComponent:
        def __init__(self):
            if not is_asyncio_available():
                raise ValueError(
                    f"{MyComponent.__qualname__} requires the asyncio support. "
                    f"Make sure you have configured the asyncio reactor in the "
                    f"TWISTED_REACTOR setting. See the asyncio documentation "
                    f"of Scrapy for more information."
                )

.. autofunction:: scrapy.utils.asyncio.is_asyncio_available
.. autofunction:: scrapy.utils.reactor.is_asyncio_reactor_installed


.. _asyncio-windows:

Windows-specific notes
======================

The Windows implementation of :mod:`asyncio` can use two event loop
implementations, :class:`~asyncio.ProactorEventLoop` (default) and
:class:`~asyncio.SelectorEventLoop`. However, only
:class:`~asyncio.SelectorEventLoop` works with Twisted.

Scrapy changes the event loop class to :class:`~asyncio.SelectorEventLoop`
automatically when you change the :setting:`TWISTED_REACTOR` setting or call
:func:`~scrapy.utils.reactor.install_reactor`.

.. note:: Other libraries you use may require
          :class:`~asyncio.ProactorEventLoop`, e.g. because it supports
          subprocesses (this is the case with `playwright`_), so you cannot use
          them together with Scrapy on Windows (but you should be able to use
          them on WSL or native Linux).

.. _playwright: https://github.com/microsoft/playwright-python


.. _using-custom-loops:

Using custom asyncio loops
==========================

You can also use custom asyncio event loops with the asyncio reactor. Set the
:setting:`ASYNCIO_EVENT_LOOP` setting to the import path of the desired event
loop class to use it instead of the default asyncio event loop.


.. _disable-asyncio:

Switching to a non-asyncio reactor
==================================

If for some reason your code doesn't work with the asyncio reactor, you can use
a different reactor by setting the :setting:`TWISTED_REACTOR` setting to its
import path (e.g. ``'twisted.internet.epollreactor.EPollReactor'``) or to
``None``, which will use the default reactor for your platform. If you are
using :class:`~scrapy.crawler.AsyncCrawlerRunner` or
:class:`~scrapy.crawler.AsyncCrawlerProcess` you also need to switch to their
Deferred-based counterparts: :class:`~scrapy.crawler.CrawlerRunner` or
:class:`~scrapy.crawler.CrawlerProcess` respectively.
