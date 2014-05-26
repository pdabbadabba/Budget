#!/usr/bin/env python

import yaml
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys
import locale
import logging

locale.setlocale( locale.LC_ALL, '' )

stream = open("params.yaml", 'r')
params = yaml.load(stream)

start_date = datetime.strptime(params["start_date"], '%m/%d/%Y').date()
date_inc = relativedelta(months=6)
current_date = start_date

accounts = {}
allocations = {}
income_sources = []
expenses = []
taxes = []

def get_freq(str_freq):
	if str_freq == "quarterly":
		return relativedelta(months=3)
	elif str_freq == "monthly":
		return relativedelta(months=1)
	elif str_freq == "2wks":
		return relativedelta(weeks=2)
	elif str_freq == "year":	
		return relativedelta(years=1)
	elif str_freq == "yearly":			
		return relativedelta(years=1)

class Account(object):
	balance = None
	last_compounded = None
	def __init__(self, name, interest_rate, compounds, balance=0):
		self.balance = balance
		self.interest_rate = interest_rate
		self.compounds = compounds
		self.name = name

	def compound(self):
		self.balance = self.balance * (1 + self.interest_rate)


	def credit(self, amount):
		self.balance += amount

class Tax:
	def __init__(self):
		pass

class Expense(object):
	expense_name = None
	frequency = None
	amount = None
	amount_per = None
	first_payment  = None
	prev_payment = None
	account = None
	last_payment = None

	def __init__(self):
		pass

	def get_amount_due(self):
		d = datetime.now()
		amount = self.amount / (((d+self.amount_per)-d).total_seconds() / ((d+self.frequency)-d).total_seconds())
		return amount

	def debit(self, accounts):
		amount = self.get_amount_due()
		accounts[self.account].credit(-1 * amount)
		#print "%s: %s debited from %s" % (self.expense_name, locale.currency(amount), self.account)

	@staticmethod	
	def from_dict(in_dict):
		expense = Expense()

		expense.expense_name = in_dict['expense_name']
		expense.frequency = get_freq(in_dict['frequency'])
		expense.amount = in_dict['amount']
		expense.amount_per = get_freq(in_dict['amount_per'])
		expense.first_payment = datetime.strptime(in_dict['first_payment'], '%m/%d/%Y').date()
		expense.account = in_dict['account']
		if 'last_payment' in in_dict: expense.last_payment =  datetime.strptime(in_dict['last_payment'], '%m/%d/%Y').date()

		return expense

class Income(object):

	source_name = None
	frequency = None
	amount = None
	amount_per = None
	first_payment  = None
	prev_payment = None
	taxes = []
	allocation = None
	last_payment = None

	def __init__(self):
		pass

	def credit_accounts(self, accounts, taxes):
		d = datetime.now()
		gross = self.amount / (((d+self.amount_per)-d).total_seconds() / ((d+self.frequency)-d).total_seconds())

		for k,v in self.allocation['pretax'].iteritems():
			if k != 'PASSTHROUGH':
				accounts[k].credit(gross * v)
				#print "%s: %s credited to %s" % (self.source_name, locale.currency(gross*v), k)
			else:
				gross = gross * v

		tax_amts = []

		for t in taxes:
			if t.id in self.taxes: tax_amts.append(t.rate * gross)

		net = gross

		for x in tax_amts: 
			net -= x

		for k,v in self.allocation['posttax'].iteritems():
			 accounts[k].credit(net * v)
			 #print "%s: %s credited to %s" % (self.source_name, locale.currency(net*v), k)


	@staticmethod	
	def from_dict(in_dict):
		income = Income()

		income.source_name = in_dict['source_name']
		income.frequency = get_freq(in_dict['frequency'])
		income.amount = in_dict['amount']
		income.amount_per = get_freq(in_dict['amount_per'])
		income.first_payment = datetime.strptime(in_dict['first_payment'], '%m/%d/%Y').date()
		income.taxes = in_dict['taxes']
		income.allocation = in_dict['allocation']
		if 'last_payment' in in_dict: income.last_payment =  datetime.strptime(in_dict['last_payment'], '%m/%d/%Y').date()
		return income


for a in params['accounts']:
  accounts[a['account_name']] = Account(a['account_name'], a['interest_rate'], get_freq(a['compounds']), a['balance'])

for i in params['incomes']:
	income_sources.append(Income.from_dict(i))

for i in params['expenses']:
	expenses.append(Expense.from_dict(i))

for t in params['trans_tax']:
	tx = Tax()
	tx.name = t['tax_name']
	tx.id = t['tax_id']
	tx.rate = t['rate']
	taxes.append(tx)

while 1:


	previous_date = current_date
	current_date = current_date + date_inc

	op_date = previous_date + relativedelta(days=1)

	print current_date
	print ""

	while op_date <= current_date:

		for account_key in accounts:

			account = accounts[account_key]

			if (not account.last_compounded and (op_date >= start_date + account.compounds)) or (account.last_compounded and op_date == (account.last_compounded + account.compounds)):
				account.compound()
				account.last_compounded = op_date 

		for income in income_sources:
			if not (income.last_payment and op_date > income.last_payment):
				if (not income.prev_payment and op_date == income.first_payment) or (income.prev_payment and op_date == (income.prev_payment + income.frequency)):
					income.prev_payment = op_date
					income.credit_accounts(accounts, taxes)

		for expense in expenses:

			if not (expense.last_payment and op_date > expense.last_payment):
			 	if (not expense.prev_payment and op_date == expense.first_payment) or (expense.prev_payment and op_date == (expense.prev_payment + expense.frequency)):
			 		expense.prev_payment = op_date
			 		amount = expense.debit(accounts)

		op_date = op_date + relativedelta(days=1)
	


	print ""

	for a in accounts:
		print ("%s: %s" % (accounts[a].name, locale.currency(accounts[a].balance, symbol=True, grouping=True))).upper()

	print "--------------------"

	sys.stdin.read(1)

