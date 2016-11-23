#!/usr/bin/env python
# python > 3.5
import time
import requests
import subprocess


class Factom(object):
    """
    All arguments optional
    Args:
        factomd: Starts daemon binary                                                                         (Bool)
        fctwallet: Starts wallet binary                                                                       (Bool)
        showbin: Opens binaries in console, if false run as background process, stdout passed to python.      (Bool)
        binpath: Needed if binaries aren't in PATH                                                            (String)
        daemonport: Use for alternate port, defaults to 8088                                                  (String)
        walletport: Use for alternate port, defaults to 8089                                                  (String)
    """
    def __init__(self, factomd=False, fctwallet=False, binpath='', daemonport='8088', walletport='8089', showbin=True):
        self.binpath = binpath
        self.factomd, self.fctwallet = None, None  # one-line fix for NameError exceptions on close
        self.dport, self.wport = daemonport, walletport
        self.headers = {'Content-type': 'application/json'}
        if factomd or fctwallet:
            self.startbinaries(factomd, fctwallet, showbin)

    def apiquery(self, command, port, method='GET', data=None, json=None, params=None, headers=None):
        url = 'http://localhost:' + port + '/v1/' + command
        print(url)
        print(data)
        print(json)
        try:
            return requests.request(method, url, data=data, json=json, params=params, headers=headers).json()
        except requests.ConnectionError:
            print('Error connecting to port: ' + port + ' - Check factomd/fctwallet is running')
            return False

    def startbinaries(self, factomd, fctwallet, showbinaries=True):
        showbin = subprocess.CREATE_NEW_CONSOLE if showbinaries else 0
        try:
            if factomd:
                self.factomd = subprocess.Popen(self.binpath + 'factomd', creationflags=showbin)
                print('Starting factomd')
            if fctwallet:
                self.fctwallet = subprocess.Popen(self.binpath + 'fctwallet', creationflags=showbin)
                print('Starting fctwallet')
        except OSError:
            print('Error opening binaries, check PATH or add binpath argument')
            return False

    def closebinaries(self):
        if self.factomd:
            print('Closing factomd')
            self.factomd.kill()
        if self.fctwallet:
            print('Closing fctwallet')
            self.fctwallet.kill()
        self.factomd, self.fctwallet = None, None #stops error on repeat attempts

    #############
    # Functions #
    #############

    def addecoutput(self, txname, ecaddress, amount):
        factoshis = self.fct_to_factoshi(amount)
        data = [('key', txname), ('name', ecaddress), ('amount', factoshis)]
        return self.apiquery('factoid-add-ecoutput/', method='POST', data=data, port=self.wport)

    def addfee(self, txname, inputaddress):
        data = [('key', txname), ('name', inputaddress)]
        return self.apiquery('factoid-add-fee/', method='POST', data=data, port=self.wport)

    def addinput(self, txname, inputaddress, amount):
        factoshis = self.fct_to_factoshi(amount)
        data = [('key', txname), ('name', inputaddress), ('amount', factoshis)]
        return self.apiquery('factoid-add-input/', method='POST', data=data, port=self.wport)

    def addoutput(self, txname, outputaddress, amount):
        factoshis = self.fct_to_factoshi(amount)
        data = [('key', txname), ('name', outputaddress), ('amount', factoshis)]
        return self.apiquery('factoid-add-output/', method='POST', data=data, port=self.wport)

    def balances(self, json=True):
        """returns json if necessary - {'Factoids':{Address:{Name, Amount}, 'EntryCredits':{Address:{Name, Amount}}"""
        query = self.apiquery('factoid-get-addresses/', port=self.wport)
        if json:
            return self.jsonbalances(query)
        else:
            return query

    def blockhead(self):
        return self.apiquery('directory-block-head/', port=self.dport)

    def composechain(self, ecaddress, extids, content=''):
        params = {"ExtIDs": extids, "Content": content}
        data = [('ExtIDs', extids), ('Content', content)]
        return self.apiquery('compose-chain-submit/' + ecaddress, method='POST', json=params, port=self.wport,
                             headers=self.headers)

    def composeentry(self, ecaddress, chainid, extids, content):
        data = {"ChainID": chainid, "ExtIDs": extids, "Content": content}
        return self.apiquery('compose-entry-submit/' + ecaddress, method='POST', data=data, port=self.wport,
                             headers=self.headers)

    def commitchain(self, chaincommit):
        """Requires 'ChainCommit' from composechain"""
        return self.apiquery('commit-chain/', method='POST', data=chaincommit, port=self.dport, headers=self.headers)

    def commitentry(self, entrycommit):
        """Requires 'EntryCommit' from composeentry"""
        return self.apiquery('commit-entry/', method='POST', data=entrycommit, port=self.dport, headers=self.headers)

    def deletetransaction(self, name): #TODO: Test
        return self.apiquery('factoid-delete-transaction/' + name, method='POST', port=self.wport)

    def dirblockmr(self, blockhash):
        """Returns directory block associated with the given hash"""
        return self.apiquery('directory-block-by-keymr/' + blockhash, port=self.dport)

    def ecaddress(self, name=''):
        return self.apiquery('factoid-generate-ec-address/' + name, port=self.wport)

    def ecbalance(self, ecaddress):
        """ Returns Entry Credit balance from wallet, name or address can be used"""
        return self.apiquery('entry-credit-balance/' + ecaddress, port=self.wport)

    def ecbalance_d(self, ecaddress):
        """ Returns Entry Credit balance from daemon, address only"""
        hexaddress = bytearray(ecaddress, 'UTF-8').hex()
        print('hexaddress: ', hexaddress) #TODO: test
        return self.apiquery('entry-credit-balance/' + hexaddress, port=self.dport)

    def factoidbalance(self, fctaddress):
        query = int(self.apiquery('factoid-balance/' + fctaddress, port=self.wport)['Response'])
        return self.factoshi_to_fct(query)

    def fctaddress(self, name=''):
        return self.apiquery('factoid-generate-address/' + name, port=self.wport)

    def getfee(self):
        return self.apiquery('factoid-get-fee/', port=self.wport)['Response']

    def height(self):
        """Returns current directory block height."""
        return self.apiquery('directory-block-height/', port=self.dport)['Height']

    def importecaddress(self, privatekey, name):
        """Adds Entry Credit Address to wallet"""
        return self.apiquery('factoid-generate-ec-address-from-human-readable-private-key/?name=' +
                             name + '&privateKey=' + privatekey, port=self.wport)

    def importfctaddress(self, privatekey, name):
        """Adds Factoid address to wallet"""
        return self.apiquery('factoid-generate-address-from-human-readable-private-key/?name=' +
                             name + '&privateKey=' + privatekey, port=self.wport)

    def newtransaction(self, name):
        return self.apiquery('factoid-new-transaction/' + name, method='POST', port=self.wport)

    def properties(self):
        """Returns version details"""
        return self.apiquery('properties/', port=self.wport)['Response']

    def revealentry(self, entrycommit):
        """ requires 'CommitEntryMsg' returned from compose-entry-submit"""
        return self.apiquery('reveal-entry/', method='POST', data=entrycommit, port=self.dport, headers=self.headers)

    def revealchain(self, chaincommit):
        """ requires 'ChainCommit' returned from compose-chain-submit"""
        return self.apiquery('reveal-chain/', method='POST', data=chaincommit, port=self.dport, headers=self.headers)

    def signtransaction(self, txname):
        return self.apiquery('factoid-sign-transaction/' + txname, method='POST', port=self.wport)

    def showtransactions(self):
        return self.apiquery('factoid-get-transactions/', port=self.wport)

    def subfee(self, txname, outputaddress):
        data = [('key', txname), ('name', outputaddress)]
        return self.apiquery('factoid-sub-fee/', method='POST', data=data, port=self.wport)

    def submit(self, txname):
        """Submit the transaction specified by txname"""
        tx = '{"Transaction":"' + txname + '"}'
        return self.apiquery('factoid-submit/' + tx, method='POST', port=self.wport)

    ##########
    # MACROS #
    ##########

    def createchain(self, ecaddress, extids, content):
        """Creates a new chain, first extid is chain name, content contains chain description"""
        compose = self.composechain(ecaddress, extids, content)
        print(compose)
        a = compose['ChainCommit']
        print(a)
        commit = self.commitchain()
        time.sleep(2)
        reveal = self.revealchain(compose['ChainCommit'])
        return reveal['Success']

    def entry(self, ecaddress, chainid, extids=[], content=''):
        data = {'ChainID': chainid, 'ExtIDs': extids, "Content": content}
        compose = self.composeentry(ecaddress, data)
        self.commitentry(compose['EntryCommit'])
        time.sleep(2)
        self.revealentry(compose['EntryReveal'])

    def purchase_ec(self, fctaddress, ecadress, fctamount, txname=None):  ###
        """
        Converts Factoids into Entry Credits
        txname optional, timestamped if left blank
        Args:
            fctaddress: Factoid Address (String)
            ecaddress:  Entry Credit Address (String)
            fctamount:  Amount in Factoids to be converted (Float or Int)
            txname:     Transaction name as recorded in wallet, not sent to blockchain (String)
        Returns:
            True if transaction successful else False
        """
        txname = txname if txname else self.autoTxName()
        print('Attempting to purchase ' + str(fctamount * self.inversefee()) + ' Entry Credits',
              self.newtransaction(txname)['Response'],
              self.addinput(txname, fctaddress, fctamount)['Response'],
              self.addecoutput(txname, ecadress, fctamount)['Response'],
              self.addfee(txname, fctaddress)['Response'],
              self.signtransaction(txname)['Response'])
        outcome = self.submit(txname)
        print(outcome['Response'])
        return outcome['Success']

    def transfer(self, input, output, amount, txname=None):  ###
        """
        Sends Factoids from input address to output address
        txname optional, timestamp if left blank

        Args:
            input:  Factoid address sending (String)
            output: Factoid address receiving (String)
            amount: Amount to be sent (Float or Int)
            txname: Transaction name in wallet for reference, not sent to blockchain (String)
        Returns:
            True if transaction successful else False
        """
        txname = txname if txname else self.autoTxName()
        print(self.newtransaction(txname)['Response'],
              self.addinput(txname, input, amount)['Response'],
              self.addoutput(txname, output, amount)['Response'],
              self.addfee(txname, input)['Response'],
              self.signtransaction(txname)['Response'])
        outcome = self.submit(txname)
        print(outcome['Response'])
        return outcome['Success']

    ####################
    # HELPER FUNCTIONS #
    ####################

    def autoTxName(self):
        return str(int(time.time() * 100))

    def factoshi_to_fct(self, factoshis):
        return str(int(factoshis * (10**-8)))

    def fct_to_factoshi(self, fct):
        return str(int(fct * (10 ** 8)))

    def inversefee(self):
        return round(1/float(self.getfee()))

    def jsonbalances(self, balances):
        try:
            balances = balances['Response'].split()
            factoids, entrycredits = {}, {}
            i = 2
            while balances[i] + balances[i+1] != 'Entry' + 'Credit':
                name, address, amount = balances[i], balances[i+1], balances[i+2]
                factoids[address] = {'Name': name, 'Amount': amount}
                i += 3
            while True:
                i += 3
                name, address, amount = balances[i], balances[i+1], balances[i+2]
                entrycredits[address] = {'Name': name, 'Amount': amount}
        except IndexError:
            return {'Factoids': factoids, 'EntryCredits': entrycredits}
