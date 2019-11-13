from odoo import models,fields,api

class product_product(models.Model):
    _inherit= 'product.product'
    
    @api.multi
    def _woo_product_count(self):
        woo_product_obj = self.env['woo.product.product.ept']
        for product in self:
            woo_products=woo_product_obj.search([('product_id','=',product.id)])
            product.woo_product_count = len(woo_products) if woo_products else 0
                           
    woo_product_count = fields.Integer(string='# Sales Count',compute='_woo_product_count')
    image_url = fields.Char(size=600, string='Image URL')    
    
class product_template(models.Model):
    _inherit= 'product.template'
    
    @api.multi
    def _woo_template_count(self):
        woo_product_template_obj = self.env['woo.product.template.ept']
        for template in self:
            woo_templates=woo_product_template_obj.search([('product_tmpl_id','=',template.id)])
            template.woo_template_count = len(woo_templates) if woo_templates else 0
                           
    woo_template_count = fields.Integer(string='# Sales',compute='_woo_template_count')    