from odoo  import models,fields

class woo_transaction_log(models.Model):
    _name="woo.transaction.log"
    _order='id desc'
    _rec_name = 'create_date'
    _description = "WooCommerce Process Job"
    create_date=fields.Datetime("Create Date")
    mismatch_details=fields.Boolean("Mismatch Details")
    message=fields.Text("Message")
    type=fields.Selection([('sales','Sales'),('product','Product'),('stock','Stock'),('price','Price'),('category','Category'),('tags','Tags'),('customer','Customer'),('coupon','Coupons'),('system_status','System Status')],string="Type")
    woo_instance_id=fields.Many2one("woo.instance.ept",string="Instance")