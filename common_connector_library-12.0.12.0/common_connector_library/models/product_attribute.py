from odoo import models,api

class product_attribute(models.Model):
    _inherit = "product.attribute"
    
    @api.multi
    def get_attribute(self,attribute_string,type='radio',create_variant='always',auto_create=False):
        attributes=self.search([('name','=ilike',attribute_string),('create_variant','=',create_variant)])
        if not attributes:
            if auto_create:
                return self.create(({'name':attribute_string,'create_variant':create_variant,'type':type}))
            else:
                return False
        else:
            return attributes