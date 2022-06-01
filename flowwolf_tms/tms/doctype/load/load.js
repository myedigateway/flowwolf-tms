// Copyright (c) 2022, Flowwolf Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Load', {
	refresh: function(frm) {
		if(!frm.is_new()) {
			frm.trigger("show_xml_dialog");
		}
	},
	show_xml_dialog(frm) {
		frm.add_custom_button(__('Standard XML'), function() {
			frappe.call({
				method: 'get_xml',
				doc: frm.doc,
				callback: function(r) {
					if (r.message) {
						console.log(r.message);
						let d = new frappe.ui.Dialog({
							title: 'Standard XML',
							fields: [
								{
									label: 'XML',
									fieldname: 'standard_xml',
									fieldtype: 'Code',
									default: r.message,
								}
							],
							primary_action_label: 'Copy',
							primary_action(values) {
								navigator.clipboard.writeText(r.message).then(function() {
										frappe.show_alert({
											indicator: 'green',
											message: __('Copied to clipboard.')
										});
									}, function(err) {
										frappe.show_alert({
											indicator: 'red',
											message: __('Could not copy XML.')
										});
										console.error('Async: Could not copy text: ', err);
									});
								d.hide();
							}
						});
						d.show();
						
					}
				}
			}); 
		});
	}
});
