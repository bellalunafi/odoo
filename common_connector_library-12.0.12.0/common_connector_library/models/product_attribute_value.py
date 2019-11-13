from odoo import models,api

class product_attribute_value(models.Model):
    _inherit = "product.attribute.value"
    
    @api.multi
    def get_attribute_values(self,name,attribute_id,auto_create=False):
        attribute_values=self.search([('name','=ilike',name),('attribute_id','=',attribute_id)])
        if not attribute_values:
            if auto_create:
                return self.create(({'name':name,'attribute_id':attribute_id}))
            else:
                return False
        else:
            return attribute_values