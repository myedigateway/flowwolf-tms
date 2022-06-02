import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_load_xml(load):
    if not frappe.db.exists("Load", load):
        frappe.throw(_("Load not found."))
    
    load_doc = frappe.get_doc("Load", load)
    xml = load_doc.get_xml(beautify=False)
    return xml