from odoo import models,api

class product_product(models.Model):
    _inherit = "product.product"
    
    @api.multi
    def get_stock_ept(self,product_id,warehouse_id,fix_stock_type=False,fix_stock_value=0,stock_type='virtual_available'):
        product = self.with_context(warehouse=warehouse_id).browse(product_id.id)
        try:
            actual_stock = getattr(product, stock_type)
            if actual_stock >= 1.00:
                if fix_stock_type == 'fix':
                    if fix_stock_value >= actual_stock:
                        return actual_stock
                    else:
                        return fix_stock_value
    
                elif fix_stock_type == 'percentage':
                    quantity = int((actual_stock * fix_stock_value) / 100.0)
                    if quantity >= actual_stock:
                        return actual_stock
                    else:
                        return quantity
            return actual_stock
        except Exception as e:
            raise Warning(e)
