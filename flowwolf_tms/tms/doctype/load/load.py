# Copyright (c) 2022, Flowwolf Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from dicttoxml import dicttoxml
from xml.dom.minidom import parseString

field_mapping = {
	"load_id": "shipmentId",
	"stops": {
		"stop_sequence": "stopNum",
		"type": "stopReason",
		"date": "appointmentDate",
		"time": "appointmentTime",
		"location_address": "stopAddress"
	},
	"items": {}
}

hc_values = {
	"createCustomerQuote": True,
	"createEdiTransaction": True,
	"pickupStopCount": 2,
	"senderId": "penske",
	"paymentTerms": "CC",
	"purpose": 6,
}

stops_hc_values = {
	"senderId": "018076351",
	"appointmentRequired": False,
	"senderId": "penske",
	"createContact": False,
	"createLineitems": False
}

class Load(Document):
	@frappe.whitelist()
	def get_xml_(self):
		xml = self.get_xml(beautify=True)
		return xml

	@frappe.whitelist()
	def get_xml(self, beautify=True):
		# stops_list = get_stop_list()
		xml_dict = {
			"stopCount": len(self.stops),
			"stops": []
		}

		my_item_func = lambda x: x[:-1]

		fields = self.meta.get("fields", {"fieldtype": ["not in", ["Section Break", "Column Break", "Tab Break"]]})
		for field in fields:
			if field.fieldtype not in ["Table", "Table MultiSelect"]:
				if field_mapping.get(field.fieldname):
					value = self.get(field.fieldname) or none
					if field.fieldtype == "Time" and value:
						value = frappe.utils.get_time_str(value)
					
					xml_dict[field_mapping.get(field.fieldname)]= value

			elif field.fieldtype == "Table":
				child_meta = frappe.get_meta(field.options)
				child_fields = child_meta.get("fields", {"fieldtype": ["not in", ["Section Break", "Column Break", "Tab Break"]]})

				if field_mapping.get(field.fieldname):
					for row in self.get(field.fieldname):
						temp_dict = {}

						for c_field in child_fields:
							if field_mapping[field.fieldname].get(c_field.fieldname):
								value = row.get(c_field.fieldname) or None
								if c_field.fieldtype == "Time" and value:
									value = frappe.utils.get_time_str(value)[0:-3]

								temp_dict[field_mapping[field.fieldname].get(c_field.fieldname)] = value

						if globals().get(f"{field.fieldname}_hc_values"):
							temp_dict.update(globals().get(f"{field.fieldname}_hc_values"))

						xml_dict[field.fieldname].append(temp_dict)
		xml_dict = {**hc_values, **xml_dict}
		xml = dicttoxml(xml_dict, custom_root="motorcarrierLoadtender", attr_type=False, item_func=my_item_func).decode('UTF-8')
		
		if beautify:
			xml = parseString(xml)
			return str(xml.toprettyxml())

		return str(xml)

