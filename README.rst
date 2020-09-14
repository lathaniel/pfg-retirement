Principal Financial Group retirement account interaction
========================================================

The intent of this package is to allow interaction with PFG retirement accounts through Python. This is in no way affiliated with Principal Financial Group or any of its affiliates. Use of this package is done so at your own risk.

* `Documentation <https://pfg-retirement.readthedocs.io/en/latest/>`_

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
    chrome_options = webdriver.chrome.options.Options()
    chrome_options.add_argument('--headless')
    options.add_argument("--log-level=3")  # only show fatal
    driver = webdriver.Chrome(executable_path='chromedriver', options=chrome_options)
    driver.set_window_size(1440, 900)

    # Log in to the account
    session = pfg.Session(driver, 'username', 'pa$$w0rd')

    # show available accounts
    session.accounts

    # play around with one of the accounts
    acct = session.accounts(index=1) # choosing the account at index 1 of the session accounts
    acct.summary()

    # Account info
    acct.name
    acct.type    
    
    # Balance
    acct.balance
    acct.vestedBalance

    # metrics
    acct.gain # Gain/Loss
    acct.ror # Rate of Return   
    acct.name # Name of the account
    acct.type # Type of account, e.g. "Defined Contribution Retirement Plan"
    acct.category # Broad category of account, e.g. "Retirement & Investments"
    acct.ror # Rate of Return
    acct.balance # Total balance of the account
    acct.vestedBalance # Vested portion of balance
    acct.gain # Amount of gain or loss on the account
    acct.loss # alias for *gain*
    acct.asof # Date when data was updated
    acct.allocations # Summary of paycheck contribution settings as *Pandas DataFrame*
    acct.contributions # Summary of employee vs employer contributions (along with vesting information) as *Pandas DataFrame* 

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
