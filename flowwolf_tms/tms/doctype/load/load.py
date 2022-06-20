# Copyright (c) 2022, Flowwolf Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint
from dicttoxml import dicttoxml
from xml.dom.minidom import parseString
from operator import itemgetter

field_mapping = {
	"load_id": "shipmentId",
	"equipment_type": "equipmentCode",
	"distance": "distance",
	"stops": {
		"stop_sequence": "stopNum",
		"type": "stopReason",
		"date": "appointmentDate",
		"time": "appointmentTime",
		"stop": "address",
		"appointment_required": "appointmentRequired"
	},
	"items": {}
}

hc_values = {
	"createCustomerQuote": "false",
	"createEdiTransaction": "false",
	"pickupStopCount": 2,
	"senderId": "PENSKE",
	"paymentTerms": "CC",
	"purpose": "00",
	"tmsType": "Shipper/Consignee",
}

stops_hc_values = {
	"senderId": "018076351",
	"senderId": "PENSKE",
	"createContact": "false",
	"createLineitems": "false"
}

class Load(Document):
	def validate(self):
		self.sort_stop_stop_sequence()
		self.update_items()
		self.update_pickup_and_drop()

	def sort_stop_stop_sequence(self):
		for i, stop in enumerate(sorted(self.stops, key=lambda stop: stop.stop_sequence), start=1):
			stop.idx = i

	def update_items(self):
		total_pickup = sum([cint(stop.items_picked) for stop in self.get("stops")])
		total_drop = sum([cint(stop.items_dropped) for stop in self.get("stops")])
		total_items = min([total_pickup, total_drop])
		self.items = []

		for i in range(total_items):
			self.append("items", {
				"item_name": f"General Freight - {i+1}"
			})

	def update_pickup_and_drop(self):
		for stop in self.get("stops"):
			for item in self.get("items"):
				if stop.type == "pickup":
					if item.pickup_stop_location:
						continue
					else:
						item.pickup_stop_location = stop.stop
						item.pickup = frappe.db.get_value("Stop Location", stop.stop, "address_title")
						break

				elif stop.type == "drop":
					if item.drop_stop_location:
						continue	
					else:
						item.drop_stop_location = stop.stop
						item.drop = frappe.db.get_value("Stop Location", stop.stop, "address_title")
						break

	@frappe.whitelist()
	def get_xml_(self):
		xml = self.get_xml(beautify=True)
		return xml

	@frappe.whitelist()
	def get_xml(self, beautify=True):
		xml_dict = {
			"stopCount": len(self.stops),
			"orderNum": self.get("load_id"),
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
									value = frappe.utils.get_time_str(value)
									value = frappe.utils.format_time(value, "HH:mm")

								if c_field.fieldtype == "Check" and c_field.fieldname == "appointment_required":
									print(value)
									value = "true" if value else "false"

								if c_field.fieldtype == "Link" and c_field.fieldname == "stop" and c_field.options == "Stop Location":
									stop_location_doc = frappe.get_doc("Stop Location", value)

									temp_dict["lineItems"] = self.get_line_items(value)

									value = {
										"identifierCode": row.get("identifier_code"),
										"name": stop_location_doc.address_title,
										"locationCode": stop_location_doc.location_code,
										"street": stop_location_doc.address_line_1,
										"city": stop_location_doc.city,
										"state": stop_location_doc.state,
										"stateCode": stop_location_doc.state,
										"zip": stop_location_doc.postal_code,
										"countryCode": stop_location_doc.country,
										"contacts" : stop_location_doc.mobile_no,
									}

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

	def get_line_items(self, stop):
		line_items = []
		for item in self.get("items"):
			field = False

			if stop in [item.get("pickup_stop_location"), item.get("drop_stop_location")]:
				field = True

			if field:
				line_items.append({
					"name": item.item_name,
					"desc": item.item_name,
					"weight": 23,
					"handlingUnitCount": item.qty,
					"handlingUnits": "Piece"
				})

		return line_items
			

		