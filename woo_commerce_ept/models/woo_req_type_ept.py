from odoo import fields,models

class woo_req_type_ept(models.Model):
    _name='woo.req.type.ept'
    _description = "WooCommerce Reqest Type"
    
    name=fields.Char('Type')