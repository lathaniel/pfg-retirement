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
        accounts (list of *str* objects): list of accounts available

    Example:
        I prefer to use a headless chrome driver as my driver:
        
        .. code-block:: python
        
            chrome_options = webdriver.chrome.options.Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument("--log-level=3")  # only show fatal
            driver = webdriver.Chrome(executable_path='chromedriver', options=chrome_options)
            driver.set_window_size(1440, 900) # Setting window size ensures elements are clickable
        
        .. code-block:: python

            session = Session(driver, 'username', 'pa$$w0rd')

    '''
    def __init__(self, driver, username, password):
        self.driver = driver
        # I guess the account needs a DD
        self.__login([username, password])
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
    
    def __verify_2FA(self):
        self.driver.implicitly_wait(10)  # seconds
        # Each field is its own box
        otp = input('What is the code that was texted to you? ')
        otp_xs = self.driver.find_element_by_id('otpXS')
        if not otp_xs.is_displayed():
            # Enter the passcode one char at a time
            for x in self.driver.find_elements_by_tag_name('input'):
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
        verify = self.driver.find_element_by_id('verifyButton')
        verify.click()
    
    def __requested_2FA(self):
        self.driver.implicitly_wait(10)  # seconds
        if not self.driver.find_element_by_id('otpXS'):
            return False
        return True

    def __login(self, creds):
        self.driver.implicitly_wait(10)  # seconds
        # Go to PFG login site
        url = 'https://login.principal.com/login'
        self.driver.get(url)

        # Login using credentials
        usr_field = self.driver.find_element_by_id('username')
        usr_field.clear()
        usr_field.send_keys(creds[0])
        pwd_field = self.driver.find_element_by_id('password')
        pwd_field.clear()
        pwd_field.send_keys(creds[1])

        # Accept the cookies, if applicable
        try:
            login = self.driver.find_element_by_id('continue')
            self.driver.find_element_by_id('onetrust-accept-btn-handler').click()
        except:
            pass
        login.click()

        # Make sure it worked
        if 'username or password you entered was invalid' in self.driver.page_source:
            print('Unable to login.')
            return None

        # Perform 2FA, if applicable
        if self.__requested_2FA():
            self.__verify_2FA()

    @property
    def accounts(self):
        return [x.name for x in self.__accounts] if self.__accounts else None
    
    @accounts.setter
    def accounts(self, value):
        self.__accounts = value
    
    def get_account(self, name=None, index=None):
        '''Retrieves the specified account from self.accounts
        
        Args:
            name (str): string matching one of the strings shown in *accounts* list
            index (int): integer for which index from *accounts* list to show
        
        Examples:
            .. code-block:: python

                session = pfg.Session(driver, usr, pwd)
                session.accounts
                # ['Company X 401k', 'Former Company Y 401k', 'Company X Pension', 'Company X Dental']
                x = session.get_account(name='Company X 401k')
                y = session.get_account(index = 0)
                x == y
                #True

            Or maybe:
            
            .. code-block:: python

                print(session.get_account(session.accounts[0]).name)
                # 'Company X 401k'
              
        '''
        if name:
            if isinstance(name, str):
                '''Case 1: a string was proided. This should represent one of the account names'''
                return list(filter(lambda x: name in x.name, self.__accounts))[0]
            else:
                print('name should be a string.')
                return None
        elif index is not None:
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
    ''':class: Account represents an account identified by the :class: `Session`
        
    Attributes:
        name (str): Name of the account
        type (str): Type of account, e.g. "Defined Contribution Retirement Plan"
        category (str): Broad category of account, e.g. "Retirement & Investments"
        ror: Rate of Return
        balance: Total balance of the account
        vestedBalance: Vested portion of balance
        gain: Amount of gain or loss on the account
        loss: alias for *gain*
        asof: Date when data was updated
        allocations: Summary of paycheck contribution settings as *Pandas DataFrame*
        contributions: Summary of employee vs employer contributions (along with vesting information) as *Pandas DataFrame*
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

    def history(self, detail='summary', start=None, end=None):
        # TODO: Include param for level of detail (summary, _, full)
        # ? when none: 'There are no transaction details available for this date range.' on page
        '''Retrieves history for the given dates for the account object

        Args:
            detail (str): Level of detail to provide. Goal is to provide three levels of detail
            start (str): Date string formatted MM/DD/YY.
                This is the beginning of the requested date range. Must be at most 92 days before *end*
            end (str): Date string formatted MM/DD/YY.
                This is the end of the requested date range. Must be at most 92 days after *start*
        
        Returns:
            Pandas Dataframe

        '''
        
        if detail.lower()=='summary':
            # Get the balanceHistory data
            transactions = pd.DataFrame(np.array([[x['effectiveDate'][0:10], x['total']] for x in self.balanceHistory]), columns = ['Date', 'Total'])

        elif detail.lower()=='full':
            #Get the most amount of detail possible

            # TODO: input validation:
            # Verify that end - start is <= 91 days
            # Veryify start and end are dates

            #? 'https://secure05.principal.com/RetirementServiceCenter/memberview?Contract=%283%2966776&Allow365=&From=06%2F13%2F2020&From2=09%2F01%2F2020&To=09%2F13%2F2020&To2=09%2F13%2F2020&Inv=By&Cont=By&page_name=reqbyby'
            # TODO: Build request URL using above as a template in following call
            self._request_history()
            # Let the page load
            time.sleep(4)
            
            # At this point, we've made it to the transactions - and it should be loaded already            
            tables = pd.read_html(self.driver.page_source)[1:-1]
            for i, t in enumerate(tables):
                # Each table is a multiindex along column axis
                inv = t.columns[0][0]
                t = t.droplevel(0,'columns')
                t['Investment'] = inv
                
                # Drop total row
                t = t.loc[~(t['Contribution Type']=='Total')]
                if not i:
                    transactions = pd.DataFrame(columns=t.columns)
                transactions = transactions.append(t, ignore_index=True)
                
        return transactions

    def _get_investments(self):
        '''Gets summary of current investments

        Data returned: fund manager, fund name, number of shares, share price, percent of portfolio, and total value
            
        
        Returns:
            Pandas Dataframe
        
        '''
        # ?when none: 'This option will become available once there is a balance in your account.' on page
        self._view_investments()

        # Get the name of the Advisors
        tbl = self.driver.find_element_by_tag_name('tbody')
        advisors = self._getAdvisorNames(tbl)

        # Let the page load
        time.sleep(5)
        tbl = pd.read_html(self.driver.page_source)[0]

        tbl.columns = ['AssetClass', 'Manager-Asset','Mix', 'Units', 'UnitValue', 'Total']
        tbl['Manager'] = advisors
        tbl['AssetName'] = tbl.apply(lambda x: x['Manager-Asset'].replace(x['Manager'], '').replace('Performance Snapshot', '') if not pd.isna(x['Manager']) else x['Manager-Asset'], axis=1)

        return tbl[['AssetClass', 'Manager', 'AssetName', 'Mix', 'Units', 'UnitValue', 'Total']]

    def _view_investments(self):
        self.driver.get(self.nav_links['Investment Details'])

    def _view_transactions(self):
        self.driver.get(self.nav_links['Account History'])

    def _get_allocations(self):
        '''Get the current paycheck contribution percentages
        
        Returns:
            Pandas DataFrame
        
        TODO:
            Be able to strip assetName and managerName from provided data
        '''
        self.driver.get(self.nav_links['Paycheck Contribution Details'])
        time.sleep(4) # let the page load

        tbl = pd.read_html(self.driver.page_source)[0].droplevel(0, axis=1)
        tbl.columns = ['AssetClass','Manager-Asset', 'empty', 'Allocation']
        
        # Remove unnecessary columns and rows
        tbl = tbl.drop(columns=['empty'])
        tbl = tbl.drop(len(tbl) - 1) # Last row is a total row
        tbl['Allocation'] = tbl.Allocation.apply(lambda x: float(re.search('(\d+\.\d{2})%',x)[1])/100)
        
        # Get the asset and manager names from provided column
        tbl['AssetName'] = tbl['Manager-Asset'].apply(lambda x: 'Principal' + ''.join(x.replace('Performance Snapshot', '').split('Principal')[1:]))
        # Add the fund manager
        tbl['Manager'] = tbl['Manager-Asset'].apply(lambda x: ''.join(x.replace('Performance Snapshot', '').split('Principal')[0]))

        return tbl[['Manager-Asset', 'AssetClass', 'Allocation']]

    def _request_history(self, detail='full', start=None, end=None):
        self.driver.implicitly_wait(10)
        # Go to the transactions page
        self._view_transactions()
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

    def _getAdvisorNames(self, tbl, total_row = True):
        # Take in a table and return an array with the advisor names

        advisors =  [x.text for x in tbl.find_elements_by_tag_name('em')]
        if total_row==True:
            advisors.extend([np.nan]) # Extend for total row
        
        return advisors

    def _get_contributions(self):
        self.driver.get(self.nav_links['Contribution Totals By Source'])
        # Let the page load
        time.sleep(4)
        
        # This is the most generalized table, so we'll take that. May want to provide flexibility later on, though.
        tbl = pd.read_html(driver.page_source)[1].dropna()
        tbl.columns = ['src','vested_pct','vested_usd','total_usd','total_pct']

        tbl['Source'] = tbl['src'].apply(lambda x: re.search('(.+)Summary', x)[1])

        # Change to actual numbers
        tbl.vested_pct = tbl.vested_pct.str.strip('%').astype(float)
        tbl.total_pct = tbl.total_pct.str.strip('%').astype(float)
        tbl.vested_usd = tbl.vested_usd.str.replace('$', '').str.replace(',','').astype(float)
        tbl.total_usd = tbl.total_usd.str.replace('$', '').str.replace(',','').astype(float)

        return tbl[['Source','vested_pct','vested_usd','total_usd','total_pct']]

    def _return(self, date_from = None, date_to = None, range = 'YTD'):
        '''Get the rate of return broken down by asset holdings

        Args:
            date_from (str or datetime-like obj): Start of range for which to calculate return. Default is start of year.
            date_to (str or datetime-like obj): End of range for which to calculate return. Default is current date.
            range (str): An alternative to providing *from* and *to* dates.

                *"YTD" (default)*: See year-to-date return
                *"YOY"*: See year-over-year return (1 year ago through)
                *"MAX"*: See year-over-year return for max date range (two years)
            
        Returns:
            Pandas dataframe

        '''
        self.driver.get(self.nav_links['Personalized Rate of Return'])
        # Let the page load
        time.sleep(4)

        # Get the name of the Advisors
        tbl = self.driver.find_element_by_tag_name('tbody')
        advisors = self._getAdvisorNames(tbl)

        tables = pd.read_html(self.driver.page_source)
        
        if len(tables):
            tbl = tables[0].dropna(1)
            tbl.columns = ['Manager-Asset', 'Balance', 'Return']
            tbl['Manager'] = advisors
            tbl['AssetName'] = tbl.apply(lambda x: x['Manager-Asset'].replace(x['Manager'], '').replace('Performance Snapshot', '') if not pd.isna(x['Manager']) else x['Manager-Asset'], axis=1)
            return tbl[['Manager', 'AssetName', 'Balance', 'Return']]
        else:
            return []

    @property
    def roi(self):
        return self._return()

    @property
    def allocations(self):
        return self._get_allocations()
    
    @property
    def conntributions(self):
        return self._get_contributions()
    
    @property
    def investments(self):
        return self._get_investments()

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
    
    @property
    def asof(self):
        return self.accountBalance['asOfDate'][:10]
