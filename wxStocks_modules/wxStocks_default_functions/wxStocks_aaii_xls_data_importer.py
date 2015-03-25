import sys, pprint, os, inspect, string, time

def line_number():
	"""Returns the current line number in our program."""
	return "File: %s\nLine %d:" % (inspect.getframeinfo(inspect.currentframe()).filename.split("/")[-1], inspect.currentframe().f_back.f_lineno)

try:
	import modules.xlrd as xlrd # AAII is all excel files
except:
	print line_number(), "Error: xlrd is not installed"
	sys.exit()

from wxStocks_modules import wxStocks_utilities as utils
from wxStocks_modules.wxStocks_classes import Stock, Account
from wxStocks_modules import wxStocks_db_functions as db


all_attribute_list = []
all_attribute_dict = {}
duplicate_list = []
duplicate_tuple_list = []
files_that_have_duplicates = []
files_that_are_all_duplicates = []

### xlrd functions
def return_relevant_spreadsheet_list_from_workbook(xlrd_workbook):
	relevant_sheets = []
	for i in range(xlrd_workbook.nsheets):
		sheet = xlrd_workbook.sheet_by_index(i)
		#print line_number(), sheet.name
		if sheet.nrows or sheet.ncols:
			print line_number(), "rows x cols:", sheet.nrows, sheet.ncols
			relevant_sheets.append(sheet)
		else:
			print line_number(), "is empty"
	return relevant_sheets
def return_xls_cell_value(xlrd_spreadsheet, row, column):
	return xlrd_spreadsheet.cell_value(rowx=row, colx=column)

def import_aaii_files_from_data_folder():
	""""import aaii .xls files"""
	current_directory = os.path.dirname(os.path.realpath(__file__))
	parent_directory = os.path.split(current_directory)[0]
	grandparent_directory = os.path.split(current_directory)[0]
	great_grandparent_directory = os.path.split(grandparent_directory)[0]
	data_directory = os.path.join(great_grandparent_directory, "AAII_data_import_folder")

	aaii_filenames = [filename for filename in os.listdir(data_directory) if os.path.isfile(os.path.join(data_directory, filename)) and filename != "!.gitignore"]

	expired_data = []
	for filename in aaii_filenames:
		current_time = time.time()
		one_week_in_seconds = 604800
		file_stats = os.stat(data_directory + "/" + filename)
		file_last_modified_epoch = file_stats.st_mtime # last modified
		#print filename, "last modified:", file_stats.st_mtime
		if (current_time - one_week_in_seconds) > file_last_modified_epoch:
			expired_data.append(filename)
	if expired_data:
		print line_number(), "Error: Files\n\t", "\n\t".join(expired_data), "\nare expired data. You must update."
		sys.exit()

	for filename in aaii_filenames:
		print line_number(), "processing file %d of %d" % (aaii_filenames.index(filename), len(aaii_filenames) )
		if "_Key.XLS" in filename:
			continue
		key_dict = process_aaii_xls_key_file(data_directory + "/" + filename[:-4] + "_Key.XLS")
		process_aaii_xls_data_file(data_directory + "/" + filename, key_dict)
	db.save_GLOBAL_STOCK_DICT()
	print line_number(), "AAII import complete."

def process_aaii_xls_key_file(filename):
	xlrd_workbook = xlrd.open_workbook(filename)
	relevant_spreadsheet_list  = return_relevant_spreadsheet_list_from_workbook(xlrd_workbook)

	# only 1 sheet
	if not len(relevant_spreadsheet_list) == 1:
		print line_number(), ""
		print line_number(), "Error in process_sample_dot_xls() in wxStocks_xls_import_functions.py"
		print line_number(), "spreadsheet list > 1 sheet"
		print line_number(), ""
		return None
	spreadsheet = relevant_spreadsheet_list[0]

	spreadsheet_list_of_row_data = []
	for i in range(spreadsheet.nrows):
		row_list = spreadsheet.row_values(i)
		spreadsheet_list_of_row_data.append(row_list)

	key_dict = {}
	for row_list in spreadsheet_list_of_row_data[1:]:
		key_dict[row_list[0]] = row_list[1]
	#pprint.pprint(key_dict)

	return key_dict

def process_aaii_xls_data_file(filename, key_dict):
	print line_number(), filename, "Start!"
	xlrd_workbook = xlrd.open_workbook(filename)
	relevant_spreadsheet_list  = return_relevant_spreadsheet_list_from_workbook(xlrd_workbook)
	ticker_column_string = u"ticker"

	# only 1 sheet
	if not len(relevant_spreadsheet_list) == 1:
		print line_number(), ""
		print line_number(), "Error in process_sample_dot_xls() in wxStocks_xls_import_functions.py"
		print line_number(), "spreadsheet list > 1 sheet"
		print line_number(), ""
		sys.exit()
	spreadsheet = relevant_spreadsheet_list[0]

	num_columns = spreadsheet.ncols
	num_rows = spreadsheet.nrows

	# important row and column numbers
	top_row = 0 # 1st row

	spreadsheet_list_of_row_data = []
	for i in range(spreadsheet.nrows):
		row_list = spreadsheet.row_values(i)
		spreadsheet_list_of_row_data.append(row_list)

	ticker_location = spreadsheet_list_of_row_data[0].index(u'ticker')
	#print line_number(), spreadsheet_list_of_row_data[0]


	for row_list in spreadsheet_list_of_row_data[1:]:
		current_stock = db.create_new_Stock_if_it_doesnt_exist(str(row_list[ticker_location]))
		for attribute in spreadsheet_list_of_row_data[0]:
			attribute_index = spreadsheet_list_of_row_data[0].index(attribute)
			if attribute_index == ticker_location:
				continue
			long_attribute_name = key_dict.get(attribute.upper())
			#print line_number(), long_attribute_name
			long_attribute_name = remove_inappropriate_characters_from_attribute_name(long_attribute_name)
			#print line_number(), long_attribute_name
			datum = row_list[attribute_index]
			if datum is not None:
				setattr(current_stock, long_attribute_name + "_aa", str(datum))
			else:
				setattr(current_stock, long_attribute_name + "_aa", None)

def remove_inappropriate_characters_from_attribute_name(attribute_string):
	attribute_string = str(attribute_string)
	if "Inve$tWare" in attribute_string: # weird inve$tware names throwing errors below due to "$".
		attribute_string = attribute_string.replace("Inve$tWare", "InvestWare")
	acceptable_characters = list(string.letters + string.digits + "_")
	unicode_acceptable_characters = []
	for char in acceptable_characters:
		unicode_acceptable_characters.append(unicode(char))
	acceptable_characters = acceptable_characters + unicode_acceptable_characters
	new_attribute_name = ""
	unacceptible_characters = [" ", "-", ".", ",", "(", ")", u" ", u"-", u".", u",", u"(", u")", "/", u"/", "&", u"&", "%", u"%"]
	string_fails = [char for char in unacceptible_characters if char in attribute_string]
	if string_fails:
		#print line_number(), string_fails
		for char in attribute_string:
			if char not in acceptable_characters:
				if char in [" ", "-", ".", ",", "(", ")", u" ", u"-", u".", u",", u"(", u")"]:
					new_char = "_"
				elif char in ["/", u"/"]:
					new_char = "_to_"
				elif char in ["&", u"&"]:
					new_char = "_and_"
				elif char in ["%", u"%"]:
					new_char = "percent"
				else:
					print line_number(), "Error:", char, ":", attribute_string
					sys.exit()
			else:
				new_char = str(char)

			new_attribute_name += new_char
	if new_attribute_name:
		return new_attribute_name
	else:
		return attribute_string

def import_xls_via_user_created_function(wxWindow, user_created_function):
	'''adds import csv data to stocks data via a user created function'''
	try:
		from modules import xlrd
	except:
		print line_number(), line_number(), "Error: cannot import xls file because xlrd module failed to load"
		return
	
	dirname = ''
	dialog = wx.FileDialog(wxWindow, "Choose a file", dirname, "", "*.xls", wx.OPEN)
	if dialog.ShowModal() == wx.ID_OK:
		filename = dialog.GetFilename()
		dirname = dialog.GetDirectory()
		
		#csv_file = open(os.path.join(dirname, filename), 'rb')
		
		xls_workbook = xlrd.open_workbook(dirname + "/" + filename)
		dict_list_and_attribute_suffix_tuple = user_created_function(xls_workbook)
		
	else:
		dialog.Destroy()
		return
	dialog.Destroy()
	
	# process returned tuple
	attribute_suffix = dict_list_and_attribute_suffix_tuple[1]
	success = None
	if len(attribute_suffix) != 3 or attribute_suffix[0] != "_":
		print line_number(), line_number(), "Error: your attribute suffix is improperly formatted"
		success = "fail"
		return success
	dict_list = dict_list_and_attribute_suffix_tuple[0]
	for this_dict in dict_list:
		if not this_dict:
			continue
		try:
			this_dict['stock']
		except Exception as e:
			print line_number(), e
			print line_number(), "Error: your dictionary does not have the ticker as your_dictionary['stock']"
			if success in ["success", "some"]:
				success = "some"
			else:
				success = "fail"
			continue
		stock = utils.return_stock_by_symbol(this_dict['stock'])
		if not stock:
			print line_number(), "Error: your_dictionary['stock'] does not return a recognized ticker symbol."
			if success in ["success", "some"]:
				success = "some"
			else:
				success = "fail"
			continue
		for key, value in this_dict.iteritems():
			if key == "stock":
				continue
			else:
				setattr(stock, key + attribute_suffix, value)
				if success in ["fail", "some"]:
					success = "some"
				else:
					success = "success"

	return success

def process_sample_dot_xls(xlrd_workbook, attribute_suffix = "_xl"):
	'''import sample.xls'''
	import config
	relevant_spreadsheet_list  = utils.return_relevant_spreadsheet_list_from_workbook(xlrd_workbook)

	dict_list = []
	# sample.xls specific

	# only 1 sheet
	if not len(relevant_spreadsheet_list) == 1:
		print line_number(), ""
		print line_number(), "Error in process_sample_dot_xls() in wxStocks_xls_import_functions.py"
		print line_number(), "spreadsheet list > 1 sheet"
		print line_number(), ""
		return None
	spreadsheet = relevant_spreadsheet_list[0]

	num_columns = spreadsheet.ncols
	num_rows = spreadsheet.nrows










# end of line