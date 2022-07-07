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
	"senderId": "PENSKE",
	"paymentTerms": "CC",
	"purpose": "00",
	"tmsType": "Shipper/Consignee",
}

stops_hc_values = {
	"senderId": "018076351",
	"senderId": "PENSKE",
	"createContact": "false"
}

class Load(Document):
	def validate(self):
		self.sort_stop_stop_sequence()
		self.update_items()
		self.update_pickup_and_drop()
		self.update_missing_pickup_and_drop()

	def sort_stop_stop_sequence(self):
		for i, stop in enumerate(sorted(self.stops, key=lambda stop: stop.stop_sequence), start=1):
			stop.idx = i

	def update_items(self):
		total_pickup = sum([cint(stop.items_picked) for stop in self.get("stops")])
		total_drop = sum([cint(stop.items_dropped) for stop in self.get("stops")])
		total_items = max([total_pickup, total_drop])
		self.items = []

		for i in range(total_items):
			self.append("items", {
				"item_name": f"General Freight - {i+1}"
			})

	def update_pickup_and_drop(self):
		for stop in self.get("stops"):
			if stop.type == "pickup":
				for i in range(stop.items_picked):
					for item in self.get("items"):
						if item.pickup_stop_location:
							continue
						else:
							item.pickup_stop_location = stop.stop
							item.pickup = frappe.db.get_value("Stop Location", stop.stop, "address_title")
							break

			elif stop.type == "drop":
				for i in range(stop.items_dropped):
					for item in self.get("items"):
						if item.drop_stop_location:
							continue	
						else:
							item.drop_stop_location = stop.stop
							item.drop = frappe.db.get_value("Stop Location", stop.stop, "address_title")
							break

	def update_missing_pickup_and_drop(self):
		last_pickup = None
		last_drop = None

		for stop in reversed(self.get("stops")):
			if last_pickup and last_drop:
				break
			else:
				if not last_pickup and stop.type == "pickup":
					last_pickup = stop.stop
				elif not last_drop and stop.type == "drop":
					last_drop = stop.stop
		
		last_pickup_title = frappe.db.get_value("Stop Location", last_pickup, "address_title")
		last_drop_title = frappe.db.get_value("Stop Location", last_drop, "address_title")

		for item in self.get("items"):
			if not item.pickup_stop_location:
				item.pickup_stop_location = last_pickup
				item.pickup = last_pickup_title

			if not item.drop_stop_location:
				item.drop_stop_location = last_drop
				item.drop = last_drop_title

	@frappe.whitelist()
	def get_xml_(self):
		xml = self.get_xml(beautify=True)
		return xml

	@frappe.whitelist()
	def get_xml(self, beautify=True):
		xml_dict = {
			"stopCount": len(self.stops),
			"orderNum": self.get("load_id"),
			"pickupStopCount": self.get_pickup_count(),
			"stops": []
		}

		my_item_func = lambda x: x[:-1]

		fields = self.meta.get("fields", {"fieldtype": ["not in", ["Section Break", "Column Break", "Tab Break"]]})
		for field in fields:
			if field.fieldtype not in ["Table", "Table MultiSelect"]:
				if field_mapping.get(field.fieldname):
					value = self.get(field.fieldname) or None
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

	def get_pickup_count(self):
		pickupStopCount = 0
		for stop in self.stops:
			if stop.type == "pickup":
				pickupStopCount += 1
		return pickupStopCount

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
			

		