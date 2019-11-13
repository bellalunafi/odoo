from odoo import models,api

class product_pricelist(models.Model):
    _inherit = "product.pricelist"
    
    @api.multi
    def get_product_price_ept(self,product,pricelist_id,partner=False):
        pricelist = self.browse(pricelist_id)
        price = pricelist.get_product_price(product,1.0,partner=partner,uom_id=product.uom_id.id)
        return price
        
    @api.multi
    def set_product_price_ept(self,product_id,pricelist_id,price,min_qty=1):
        product_pricelist_item_obj=self.env['product.pricelist.item']
        domain = []
        domain.append(('pricelist_id','=',pricelist_id))
        domain.append(('product_id','=',product_id))
        domain.append(('min_quantity','=',min_qty))
        product_pricelist_item =product_pricelist_item_obj.search(domain)
        if product_pricelist_item:
            product_pricelist_item.write({'fixed_price':price})
        else:
            vals = {
                'pricelist_id':pricelist_id,
                'applied_on':'0_product_variant',
                'product_id':product_id,
                'min_quantity':min_qty,
                'fixed_price':price,
            }
            product_pricelist_item_obj.create(vals)
        return product_pricelist_item
