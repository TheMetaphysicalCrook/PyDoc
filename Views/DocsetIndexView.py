
import ui
import os
from urllib.parse import quote

class DocsetIndexView (object):
	def __init__(self):
		self.data = []
		self.docset = None
		self.indexSelectCallback = None
		self.docsetType = None
		
	def tableview_did_select(self, tableview, section, row):
		if self.docsetType == 'docset':
			url = 'file://' + os.path.join(self.docset['path'], 'Contents/Resources/Documents', self.data[row]['path'])
		elif self.docsetType == 'cheatsheet':
			url = 'file://' + os.path.join(self.docset.path, 'Contents/Resources/Documents', self.data[row]['path'])
		elif self.docsetType == 'usercontributed':
			url = 'file://' + os.path.join(self.docset.path, 'Contents/Resources/Documents', self.data[row]['path'])
		url = url.replace(' ', '%20')
		self.indexSelectCallback(url)
		
	def tableview_number_of_sections(self, tableview):
		return 1
		
	def tableview_number_of_rows(self, tableview, section):
		return len(self.data)
		
	def tableview_cell_for_row(self, tableview, section, row):
		cell = ui.TableViewCell()
		cell.text_label.text = self.data[row]['name']
		cell.accessory_type = 'disclosure_indicator'
		if not self.data[row]['type'].icon == None:
			cell.image_view.image = self.data[row]['type'].icon
		return cell
	
	def update_with_docset(self, docset, indexes, indexSelectCallback, docsetType):
		self.data = indexes
		self.docset = docset
		self.indexSelectCallback = indexSelectCallback
		self.docsetType = docsetType


def get_view():
	tv = ui.TableView()
	w,h = ui.get_screen_size()
	tv.width = w
	tv.height = h
	tv.flex = 'WH'
	tv.name = 'PyDoc'
	data = DocsetIndexView()
	tv.delegate = data
	tv.data_source = data
	return tv
