'''
Module used to scrape/obtain data from Principal's Retirement account. It does so using a selenium web driver.
'''
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time, datetime
import json, re
import pandas as pd
import numpy as np

class Account:
    def __init__(self, driver, username, password):
        self.driver = driver
        #wait = WebDriverWait(self.driver, 10) 
        self.driver = login(driver, [username, password]) # I guess the account needs a DD 
        self.contracts = [] # Not sure abou this yet
    
        '''from the landing page, get the contract numbers and the id number
            We need to wait for the page to load to do this'''
        time.sleep(7)
        # Get all the hrefs from the landing page
        a_tags = driver.find_elements_by_tag_name('a')

        # Filter to ones containing 'contract_num' in the href
        a_tags = list(filter(lambda x: False if not x.get_attribute('href') else 'contract_num' in x.get_attribute('href'), a_tags))
        #TODO: Filter to only unique hrefs so we only get relevant elements
        for tag in a_tags:
            d = dict()
            href = tag.get_attribute('href')
            d['nav_url'] = href
            # Get query params from the href
            attrs = re.findall('[\\&\\?]([^\\&=\\?]+)=([^\\&\\?]+)', href)           
            
            if len(attrs):
                for param, val in attrs: 
                    d.setdefault(param, []).append(val) 

            # Get the Name of the contract
            onclick = tag.get_attribute('onclick')
            if onclick:
                # Arglist should be of form (plan_cat, plan_type, plan_name)
                argnames = ['category','type','name']
                onclick = onclick.split('gtmAccountDetails')[-1].strip('()').split(',')
                if len(onclick)==3: # This should always be case...or at least it will once I set this up correctly                    
                    # strip away the double quotes
                    argvals = list(map(lambda x: x.strip('"'), onclick))
                    d.update(dict(zip(argnames, argvals)))
                    self.contracts.append(Contract(driver = self.driver, **d))

class Contract(Account):
    def __init__(self, **kwargs):
        '''kwargs:
            id_num
            category
            type
            name
            nav_url
            driver ... I think the account should really have the driver, but I cannot seem to wrap my head around that yet.
                    Furthermore, I think each contract having its own driver will cause HTMLAsynch issues.
        '''
        self.__dict__.update(kwargs) # Update the attributes with provided params
        # just for shits, lets see what happens if we run summary() on init
        # ! Update: its a no-go
        #self.summary()
    
    def summary(self):
        '''
        use nav_url to get some info on the account (e.g. balance, vested balance, etc.)
        Matta fact, maybe this should be done on __init__, since doing so could also yield hrefs to history, etc.
        '''
        self.driver.implicitly_wait(10)
        self.driver.get(self.nav_url)
        
        # Find the nav bar (give the page time to load)
        time.sleep(5)
        self.driver.implicitly_wait(0)
        navs = self.driver.find_elements_by_tag_name('nav')
        # Assumption is that nav bar is second (first would be tope with logout etc)
        nav_bar = nav_bar = navs[1].find_element_by_tag_name('ul') if len(navs) else None
        
        # Use the dropdowns to get the hrefs
        d = dict()
        if nav_bar:
            # Get the dropdowns
            #for dd in nav_bar.find_elements_by_tag_name('ul'):

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
                    d[opt.text] = opt.find_element_by_tag_name('a').get_attribute('href') # Should only be one                    
        
        self.nav_links = d

        ########
        # Get account summary info
        m = re.search('controllerData = (\\{.*\\})\;?', self.driver.page_source)
        if m:
            d = json.loads(m[1])
            # For now just add everything, I guess
            self.__dict__.update(d)

    def history(self, start=None, end=None):
        # TODO: Include param for level of detail (mend, summ, full) 
        '''when none: 'There are no transaction details available for this date range.' on page'''
        # Verify that end - start is <= 91 days
        # Veryify start and end are dates

        # By default, get the most amount of detail possible
        self.request_history()

        # At this point, we've made it to the transactions - and it should be loaded already
        headers = None
        self.driver.implicitly_wait(0) # seconds    
        for tbl in self.driver.find_elements_by_id('ResultTable'): # This element is a table of transactions for a fund
            for t in tbl.find_elements_by_tag_name('tbody'):
                for r in t.find_elements_by_tag_name('tr'):        
                    # One of these has the investment name and the table headers    
                    if r.find_elements_by_tag_name('th'):
                        if not 'activity amount' in r.text.lower():
                            # Get the name of the investment
                            investment = r.text
                        elif not headers: # The assumption here is that all tables will have the same layout and can be combined
                            # Get the column names
                            headers = [h.text for h in r.find_elements_by_tag_name('th')]
                            
                            # Create an empty dataframe with column names (add one for fund name)
                            transactions = pd.DataFrame(columns=list(headers + ['Investment']))
                            
                    # The other has the investment details
                    else:
                        data = [d.text for d in r.find_elements_by_tag_name('td')] + [investment]
                        if data[2]=='Total':
                            continue # We don't need the total row
                        row = dict(zip(transactions.columns, data))
                        transactions = transactions.append(row, ignore_index = True)  
        return transactions

    def investments(self):
        '''Use the driver to go to the investment details page.
            Then, return a Pandas dataframe with the relevant information from said page
        '''
        '''when none: 'This option will become available once there is a balance in your account.' on page'''
        self.view_investments()

        # Let the page load
        time.sleep(5)
        tbl = pd.read_html(self.driver.page_source)[0]

        tbl.columns = ['AssetClass','Manager-Asset','Mix','Units','UnitValue','Total']
        tbl['AssetName'] = tbl['Manager-Asset'].apply(lambda x: 'Principal' + ''.join(x.replace('Performance Snapshot','').split('Principal')[1:]))
        # Add the fund manager
        tbl['Manager'] = tbl['Manager-Asset'].apply(lambda x: ''.join(x.replace('Performance Snapshot','').split('Principal')[0]))

        return tbl[['AssetClass','Manager','AssetName','Mix','Units','UnitValue','Total']]

        # Remove rows and columns that wont be used
        # Do all the following later (i.e. user-side)
        #tbl = tbl[['AssetName','Date','Close']].dropna()
        # Add date column
        #tbl['Date'] = pd.datetime.today().strftime('%Y-%m-%d')
        # Remove any funds that actually have tickers
        #tbl = tbl.loc[~(tbl.AssetName.str.contains(' CIT'))] # Think this logic is sound

        #return tbl
     
    def view_investments(self):
        # This should probably be a method of Account, but inherited to Contract?
        self.driver.get(self.nav_links['Investment Details'])
    
    def view_transactions(self):
        self.driver.get(self.nav_links['Account History'])

    def request_history(self, detail = 'full', start = None, end = None):
        self.driver.implicitly_wait(10)
        # Go to the transactions page
        self.view_transactions()
        if detail=='full':
            # View in full detail
            self.driver.find_element_by_id('submit-view-more-history').click()

        #self.driver.get('https://secure05.principal.com/RetirementServiceCenter/memberview?page_name=reqonline')

        # Select dates (MM/DD/YYYY)
        # By default: Let's choose the current date and 92 days prior
        if not start:
            start = (datetime.date.today() + datetime.timedelta(-92)).strftime('%m/%d/%Y')
        if not end:
            end = datetime.date.today().strftime('%m/%d/%Y')        

        from_field = self.driver.find_element_by_id('From')
        from_field.clear()
        from_field.send_keys(start)
        to_field = self.driver.find_element_by_id('To')
        to_field.clear()
        to_field.send_keys(end)

        if detail=='full':
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
    if not driver.find_element_by_id('otpXS'):
        return False
    return True

def verify_2FA(driver):
    # Each field is its own box
    otp = input('What is the code that was texted to you? ')
    otp_xs = driver.find_element_by_id('otpXS')
    if not otp_xs.is_displayed():
        # Enter the passcode one char at a time
        for x in driver.find_elements_by_tag_name('input'):
            if x.get_attribute('id')=='otp1':
                x.clear()
                x.send_keys(otp[0])
            elif x.get_attribute('id')=='otp2':
                x.clear()
                x.send_keys(otp[1])
            elif x.get_attribute('id')=='otp3':
                x.clear()
                x.send_keys(otp[2])
            elif x.get_attribute('id')=='otp4':
                x.clear()
                x.send_keys(otp[3])
            elif x.get_attribute('id')=='otp5':
                x.clear()
                x.send_keys(otp[4])
            elif x.get_attribute('id')=='otp6':
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
    driver.implicitly_wait(10) # seconds
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
