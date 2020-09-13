'''
Primary module used for this project.
Used to scrape/obtain data from Principal's consumer. It does so using a selenium web driver.
'''
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import datetime
import json
import re
import pandas as pd
import numpy as np


class Session:
    '''Session class represents the login session

    Parameters:
        driver (selenium.webdriver): Selenium driver instance used to interact with the webpage
        username (str): username to login
        password (str): password to login
    
    Attributes:
        accounts (list): list of accounts available

    '''
    def __init__(self, driver, username, password):
        self.driver = driver
        # I guess the account needs a DD
        self.driver = login(driver, [username, password])
        self.__accounts = []

        '''from the landing page, get the contract number(s) and the id number
            We need to wait for the page to load to do this'''
        time.sleep(7) # Maybe while 'Hang on' in page text
        # Get all the hrefs from the landing page
        a_tags = driver.find_elements_by_tag_name('a')

        # Filter to links containing 'contract' in the href
        a_tags = list(filter(lambda x: False if not x.get_attribute('href') else 'contract' in x.get_attribute('href').lower(), a_tags))
        hrefs = [x.get_attribute('href') for x in a_tags] # Do this to avoid stale element issue
        onclicks = [x.get_attribute('onclick') for x in a_tags] # Do this to avoid stale element issue

        for i, href in enumerate(hrefs):
            d = dict()
            d['nav_url'] = href
            # Get query params from the href
            attrs = re.findall('[\\&\\?]([^\\&=\\?]+)=([^\\&\\?]+)', href) if href else None

            if attrs:
                for param, val in attrs:
                    d.setdefault(param, []).append(val)

            # Get the Name of the account
            if onclicks[i]:
                # Arglist should be of form (plan_cat, plan_type, plan_name)
                argnames = ['category', 'type', 'name']
                onclick = onclicks[i].split('gtmAccountDetails')[-1].strip('()').split(',')
                # This should always be case...or at least it will once I set this up correctly
                if len(onclick) == 3:
                    # strip away the double quotes
                    argvals = list(map(lambda x: x.strip('"'), onclick))
                    d.update(dict(zip(argnames, argvals)))
                    self.add_account(Account(driver=self.driver, **d))

    @property
    def accounts(self):
        return [x.name for x in self.__accounts] if self.__accounts else None
    
    @accounts.setter
    def accounts(self, value):
        self.__accounts = value
    
    def get_account(self, name=None, index=None):
        if name:
            if isinstance(name, str):
                '''Case 1: a string was proided. This should represent one of the account names'''
                return list(filter(lambda x: name in x.name, self.__accounts))[0]
            else:
                print('name should be a string.')
                return None
        elif index:
            if isinstance(index, int):
                '''Case 2: an integer was provided. This should represent an index'''
                return self.__accounts[index]
            else:
                print('index should be an integer representing an index')
                return None
    
    def add_account(self, obj_account):
        self.__accounts = self.__accounts + [obj_account]
        return self.__accounts

class Account(Session):
    '''Account class represents an account identified by the :class: `Session`
        
    Attributes:
        name (str): Name of the account
        type (str): Type of account, e.g. "Defined Contribution Retirement"
        ror: Rate of Return
        balance: Total balance of the account
        vestedBalance: Vested portion of balance
        gain: Amount of gain or loss on the account
        loss: alias for *gain*

    Methods:
        summary: Adds summary info to the account as attributes
        history: Pulls history for the account
        investments: Pulls current investment mix
    '''
    def __init__(self, **kwargs):
        '''kwargs:
            id_num
            category
            type
            name
            nav_url
            driver ... I think the account should really have the driver, but I cannot seem to wrap my head around that yet.
                    Furthermore, I think each account having its own driver will cause HTMLAsynch issues.
        '''
        self.__dict__.update(kwargs)  # Update the attributes with provided params
        # just for shits, lets see what happens if we run summary() on init
        # ? Update: It takes about two minutes, which is kind of extra, so lets leave it out for now
        #self.summary()

    def summary(self):
        '''
        use nav_url to get some info on the account (e.g. balance, vested balance, etc.)
        Matta fact, maybe this should be done on __init__, since doing so could also yield hrefs to history, etc.
        '''
        self.driver.implicitly_wait(10)
        self.driver.get(self.nav_url)
        if 'defined contribution' in self.type.lower():

            # Find the nav bar (give the page time to load)
            time.sleep(5)
            self.driver.implicitly_wait(0)
            navs = self.driver.find_elements_by_tag_name('nav')
            # Assumption is that nav bar is second (first would be top with logout etc)
            nav_bar = nav_bar = navs[1].find_element_by_tag_name('ul') if len(navs) else None

            # Use the dropdowns to get the hrefs
            d = dict()
            if nav_bar:
                # Get the dropdowns
                # for dd in nav_bar.find_elements_by_tag_name('ul'):

                for opt in nav_bar.find_elements_by_tag_name('li'):
                    if opt.text == '':
                        continue
                    # If the opt is a dropdown
                    if opt.find_elements_by_tag_name('ul'):
                        opt.click()
                        sub = opt.find_elements_by_tag_name('li')
                        for x in sub:
                            d[x.text] = x.find_element_by_tag_name('a').get_attribute('href')
                        opt.click()
                    else:
                        d[opt.text] = opt.find_element_by_tag_name('a').get_attribute('href')  # Should only be one

            self.nav_links = d

            ########
            # Get account summary info, if available
            m = re.search(
                'controllerData = (\\{.*\\})\;?', self.driver.page_source)
            if m:
                d = json.loads(m[1])
                # For now just add everything, I guess
                self.__dict__.update(d)
        self.driver.get('https://secure05.principal.com/member/accounts') # TODO: make this an attr like Account._home

    def history(self, start=None, end=None):
        # TODO: Include param for level of detail (mend, summ, full)
        # ? when none: 'There are no transaction details available for this date range.' on page
        '''Retrieves history for the given dates for the account object

        Args:
            start (str): Date string formatted MM/DD/YY.
                This is the beginning of the requested date range. Must be at most 92 days before *end*
            end (str): Date string formatted MM/DD/YY.
                This is the end of the requested date range. Must be at most 92 days after *start*
        
        Returns:
            Pandas Dataframe

        '''
        # Verify that end - start is <= 91 days
        # Veryify start and end are dates

        # By default, get the most amount of detail possible
        self.request_history()

        # At this point, we've made it to the transactions - and it should be loaded already
        headers = None
        self.driver.implicitly_wait(0)  # seconds
        # This element is a table of transactions for a fund
        for tbl in self.driver.find_elements_by_id('ResultTable'):
            for t in tbl.find_elements_by_tag_name('tbody'):
                for r in t.find_elements_by_tag_name('tr'):
                    # One of these has the investment name and the table headers
                    if r.find_elements_by_tag_name('th'):
                        if not 'activity amount' in r.text.lower():
                            # Get the name of the investment
                            investment = r.text
                        elif not headers:  # The assumption here is that all tables will have the same layout and can be combined
                            # Get the column names
                            headers = [
                                h.text for h in r.find_elements_by_tag_name('th')]

                            # Create an empty dataframe with column names (add one for fund name)
                            transactions = pd.DataFrame(
                                columns=list(headers + ['Investment']))

                    # The other has the investment details
                    else:
                        data = [d.text for d in r.find_elements_by_tag_name(
                            'td')] + [investment]
                        if data[2] == 'Total':
                            continue  # We don't need the total row
                        row = dict(zip(transactions.columns, data))
                        transactions = transactions.append(
                            row, ignore_index=True)
        return transactions

    def investments(self):
        '''Gets summary of current investments

        Data returned: fund manager, fund name, number of shares, share price, percent of portfolio, and total value
            
        
        Returns:
            Pandas Dataframe
        
        '''


        # ?when none: 'This option will become available once there is a balance in your account.' on page
        self.view_investments()

        # Let the page load
        time.sleep(5)
        tbl = pd.read_html(self.driver.page_source)[0]

        tbl.columns = ['AssetClass', 'Manager-Asset',
                       'Mix', 'Units', 'UnitValue', 'Total']
        tbl['AssetName'] = tbl['Manager-Asset'].apply(lambda x: 'Principal' + ''.join(
            x.replace('Performance Snapshot', '').split('Principal')[1:]))
        # Add the fund manager
        tbl['Manager'] = tbl['Manager-Asset'].apply(lambda x: ''.join(
            x.replace('Performance Snapshot', '').split('Principal')[0]))

        return tbl[['AssetClass', 'Manager', 'AssetName', 'Mix', 'Units', 'UnitValue', 'Total']]

        # Remove rows and columns that wont be used
        # Do all the following later (i.e. user-side)
        #tbl = tbl[['AssetName','Date','Close']].dropna()
        # Add date column
        #tbl['Date'] = pd.datetime.today().strftime('%Y-%m-%d')
        # Remove any funds that actually have tickers
        # tbl = tbl.loc[~(tbl.AssetName.str.contains(' CIT'))] # Think this logic is sound

        # return tbl

    def view_investments(self):
        # This should probably be a method of Account, but inherited to Account?
        self.driver.get(self.nav_links['Investment Details'])

    def view_transactions(self):
        self.driver.get(self.nav_links['Account History'])

    def request_history(self, detail='full', start=None, end=None):
        self.driver.implicitly_wait(10)
        # Go to the transactions page
        self.view_transactions()
        if detail == 'full':
            # View in full detail
            self.driver.find_element_by_id('submit-view-more-history').click()

        # self.driver.get('https://secure05.principal.com/RetirementServiceCenter/memberview?page_name=reqonline')

        # Select dates (MM/DD/YYYY)
        # By default: Let's choose the current date and 92 days prior
        if not start:
            start = (datetime.date.today() +
                     datetime.timedelta(-92)).strftime('%m/%d/%Y')
        if not end:
            end = datetime.date.today().strftime('%m/%d/%Y')

        from_field = self.driver.find_element_by_id('From')
        from_field.clear()
        from_field.send_keys(start)
        to_field = self.driver.find_element_by_id('To')
        to_field.clear()
        to_field.send_keys(end)

        if detail == 'full':
            # Select detailed view (two radio buttons)
            for x in self.driver.find_elements(By.XPATH, '//label[contains(text(),"Detail by each")]'):
                x.click()

        # Submit
        btn = self.driver.find_element_by_name('Submit')
        btn.click()

    @property
    def ror(self):
        return self.accountBalance['rateOfReturn']

    @property
    def balance(self):
        return self.accountBalance['balance']

    @property
    def vestedBalance(self):
        return self.accountBalance['vestedBalance']

    @property
    def gain(self):
        return self.accountBalance['gainOrLoss']

    @property
    def loss(self):
        return self.gain


def requested_2FA(driver):
    driver.implicitly_wait(10)  # seconds
    if not driver.find_element_by_id('otpXS'):
        return False
    return True


def verify_2FA(driver):
    driver.implicitly_wait(10)  # seconds
    # Each field is its own box
    otp = input('What is the code that was texted to you? ')
    otp_xs = driver.find_element_by_id('otpXS')
    if not otp_xs.is_displayed():
        # Enter the passcode one char at a time
        for x in driver.find_elements_by_tag_name('input'):
            if x.get_attribute('id') == 'otp1':
                x.clear()
                x.send_keys(otp[0])
            elif x.get_attribute('id') == 'otp2':
                x.clear()
                x.send_keys(otp[1])
            elif x.get_attribute('id') == 'otp3':
                x.clear()
                x.send_keys(otp[2])
            elif x.get_attribute('id') == 'otp4':
                x.clear()
                x.send_keys(otp[3])
            elif x.get_attribute('id') == 'otp5':
                x.clear()
                x.send_keys(otp[4])
            elif x.get_attribute('id') == 'otp6':
                x.clear()
                x.send_keys(otp[5])
    else:
        # Enter the password all at once
        otp_xs.clear()
        otp_xs.send_keys(otp)

    # Click the verify button
    verify = driver.find_element_by_id('verifyButton')
    verify.click()

    return driver


def login(driver, creds):
    driver.implicitly_wait(10)  # seconds
    # Go to PFG login site
    url = 'https://login.principal.com/login'
    driver.get(url)

    # Login using credentials
    usr_field = driver.find_element_by_id('username')
    usr_field.clear()
    usr_field.send_keys(creds[0])
    pwd_field = driver.find_element_by_id('password')
    pwd_field.clear()
    pwd_field.send_keys(creds[1])

    # Accept the cookies, if applicable
    try:
        login = driver.find_element_by_id('continue')
        driver.find_element_by_id('onetrust-accept-btn-handler').click()
    except:
        pass
    login.click()

    # Make sure it worked
    if 'username or password you entered was invalid' in driver.page_source:
        print('Unable to login.')
        return None

    # Perform 2FA, if applicable
    if requested_2FA(driver):
        driver = verify_2FA(driver)

    return driver
