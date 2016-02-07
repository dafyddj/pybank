from threading import Thread
import requests
import time
from bs4 import BeautifulSoup
from utils import get_num

class Santander(Thread):

    accounts = []

    def __init__(self):

        Thread.__init__(self)

    def set_login_params(self, login_dict):

        self.user = login_dict['user']
        self.pin = login_dict['pin']
        self.pob = login_dict['pob']

    def run(self):

        s = requests.Session() # new requests session
        s.headers.update({'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.39 Safari/537.36'})

        try:
            r = self.login1(s)
            r = self.login2(s, r)
            r = self.login3(s, r)
            r = self.main_page(s, r)
        except:
            import traceback
            traceback.print_exc()

            acc = {'bank': 'Santander'}

            acc['name'] = 'error'

            acc['balance'] = 0
            acc['available'] = 0

            self.accounts.append(acc)

    def get_accounts(self):
        return self.accounts

    def login1(self, s):
        
        ## login 1 - id and password

        # get login page (contains form token)
        r = s.get('https://retail.santander.co.uk/LOGSUK_NS_ENS/BtoChannelDriver.ssobto?dse_operationName=LOGON')

        # get all form fields, put in dictionary d - # http://stackoverflow.com/a/32074666
        soup = BeautifulSoup(r.text, 'html.parser')
        d = {e['name']: e.get('value', '') for e in soup.find_all('input', {'name': True})}

        # add ID to dictionary
        d['infoLDAP_E.customerID'] = self.user

        # post to login page with dictionary as header data. response contains cookies
        return s.post("https://retail.santander.co.uk/LOGSUK_NS_ENS/ChannelDriver.ssobto?dse_operationName=LOGON", data=d)

    def login2(self, s, r):
        import pdb; pdb.set_trace()

        ## login 2 - challenge

        # get all form fields, put in dictionary d - # http://stackoverflow.com/a/32074666
        soup = BeautifulSoup(r.text, 'html.parser')
        d = {e['name']: e.get('value', '') for e in soup.find_all('input', {'name': True})}

        # add corresponding memorable info character to post data (prepend &nbsp; in login form options)
        d['cbQuestionChallenge.responseUser'] = self.pob

        # post to 2nd login page with dictionary as header data. r is logged in main page
        return s.post("https://retail.santander.co.uk/LOGSUK_NS_ENS/ChannelDriver.ssobto?dse_contextRoot=true", data=d)

    def login3(self, s, r):

        ## login 3 - PIN

        # get all form fields, put in dictionary d - # http://stackoverflow.com/a/32074666
        soup = BeautifulSoup(r.text, 'html.parser')
        d = {e['name']: e.get('value', '') for e in soup.find_all('input', {'name': True})}

        # add corresponding memorable info character to post data (prepend &nbsp; in login form options)
        d['authentication.CustomerPIN'] = self.pin

        # post to 3rd login page with dictionary as header data. r is logged in main page
        return s.post("https://retail.santander.co.uk/LOGSUK_NS_ENS/ChannelDriver.ssobto?dse_contextRoot=true", data=d)

    def main_page(self, s, r):
        
        soup = BeautifulSoup(r.text, 'html.parser')
      
        for accountEntry in soup.find(id = 'lstAccLst').findAll('li', recursive=False):

            # get account details and add to accounts list

            r = s.get('https://secure.tsb.co.uk' + accountEntry.find('h2').a['href'])
            soup = BeautifulSoup(r.text, 'html.parser')

            accountNumbers = soup.find(class_ = 'numbers').get_text().split(', ')
            
            acc = {'bank': 'TSB'}

            acc['name'] = soup.find('h1').get_text()
            acc['sort'] = accountNumbers[0].replace('-', '')
            acc['number'] = accountNumbers[1]

            acc['balance'] = get_num(soup.find(class_ = 'balance').get_text())
            acc['available'] = get_num(soup.find(class_ = 'manageMyAccountsFaShowMeAnchor {bubble : \'fundsAvailable\', pointer : \'top\'}').parent.get_text())
            
            self.accounts.append(acc)

            # download transaction files

            r = s.get('https://secure.tsb.co.uk' + soup.find(id = 'pnlgrpStatement:conS1:lkoverlay')['href'])
            soup = BeautifulSoup(r.text, 'html.parser')

            # get all form fields, put in dictionary d - # http://stackoverflow.com/a/32074666
            soup = BeautifulSoup(r.text, 'html.parser')
            d = {e['name']: e.get('value', '') for e in soup.find_all('input', {'name': True})}

            now = time.localtime(time.time())
            yearAgo = time.localtime(time.time() - 6570000) # ~ 2.5 months year ago

            # will download current view if 0, past 2.5 months if 1
            d['frmTest:rdoDateRange'] = '0'
            
            d['frmTest:dtSearchFromDate'] = time.strftime('%d', yearAgo) 
            d['frmTest:dtSearchFromDate.month'] = time.strftime('%m', yearAgo) 
            d['frmTest:dtSearchFromDate.year'] = str(time.strftime('%Y', yearAgo)) 

            d['frmTest:dtSearchToDate'] = time.strftime('%d', now) 
            d['frmTest:dtSearchToDate.month'] = time.strftime('%m', now)
            d['frmTest:dtSearchToDate.year'] = str(time.strftime('%Y', now))

            d['frmTest:strExportFormatSelected'] =  'Quicken 98 and 2000 and Money (.QIF)' 
            
            r = s.post('https://secure.tsb.co.uk/personal/a/viewproductdetails/m44_exportstatement_fallback.jsp', data=d)

            filename = time.strftime('%Y%m%d') + '-' + acc['sort'] + '-' + acc['number'] + '.qif'
            file = open(filename, 'w')
            file.write(r.text)
            file.close()
