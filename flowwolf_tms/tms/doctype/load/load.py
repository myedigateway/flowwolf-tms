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
	},
	"items": {}
}

hc_values = {
	"createCustomerQuote": True,
	"createEdiTransaction": True,
	"pickupStopCount": 2,
	"senderId": "12345678",
	"paymentTerms": "CC",
	"purpose": 6,
}

stops_hc_values = {
	"senderId": "018076351",
	"appointmentRequired": False
}

class Load(Document):
	@frappe.whitelist()
	def get_xml(self):
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
					
					xml_dict[field_mapping.get(field.fieldname)]= self.get(field.fieldname) or None

			elif field.fieldtype == "Table":
				child_meta = frappe.get_meta(field.options)
				child_fields = child_meta.get("fields", {"fieldtype": ["not in", ["Section Break", "Column Break", "Tab Break"]]})

				if field_mapping.get(field.fieldname):
					for row in self.get(field.fieldname):
						temp_dict = {}

						for c_field in child_fields:
							if field_mapping[field.fieldname].get(c_field.fieldname):	
								temp_dict[field_mapping[field.fieldname].get(c_field.fieldname)]= row.get(c_field.fieldname) or None

						if globals().get(f"{field.fieldname}_hc_values"):
							temp_dict.update(globals().get(f"{field.fieldname}_hc_values"))

						xml_dict[field.fieldname].append(temp_dict)
		xml_dict = {**hc_values, **xml_dict}
		xml = parseString(dicttoxml(xml_dict, attr_type=False, item_func=my_item_func).decode('UTF-8'))

		return str(xml.toprettyxml())
