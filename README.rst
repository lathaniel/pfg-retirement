Principal Financial Group retirement account interaction
========================================================

The intent of this package is to allow interaction with PFG retirement accounts through Python.

Quick Start
===========

The Account module
~~~~~~~~~~~~~~~~~~

The ``Account`` module, which allows you to login and access
your account through Python:

.. code:: python

    import pfg
    from selenium import webdriver

    # As of now, this can only be done with a selennium driver
    chrome_options = Options()
    chrome_options.add_argument('--headless') #make it headless later
    driver = webdriver.Chrome(executable_path='../chromedriver', options=chrome_options)
    driver.set_window_size(1440, 900)

    # Log in to the account
    acct = pfg.Account(driver, 'username', 'pa$$word')

    # show available accounts
    acct.contracts

Installation
------------
TODO

Requirements
------------
**TODO: Include versions below**
* `selenium webdriver <https://selenium-python.readthedocs.io/>`_
* `Python <https://www.python.org>`_
* `Pandas <https://github.com/pydata/pandas>`_
* `Numpy <http://www.numpy.org>`_