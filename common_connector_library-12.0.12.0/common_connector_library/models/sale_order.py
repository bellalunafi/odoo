from odoo import models,api

class sale_order(models.Model):
    _inherit = "sale.order"
    
    @api.multi
    def create_sales_order_vals_ept(self,vals):
        """
            required parameter :- partner_id,partner_invoice_id,partner_shipping_id,
            company_id,warehouse_id,picking_policy,date_order 
            
            Pass Dictionary
            vals = {'company_id':company_id,'partner_id':partner_id,'partner_invoice_id':partner_invoice_id,
            'partner_shipping_id':partner_shipping_id,'warehouse_id':warehouse_id,'company_id':company_id,
            'picking_policy':picking_policy,'date_order':date_order,'pricelist_id':pricelist_id,
            'payment_term_id':payment_term_id,'fiscal_position_id':fiscal_position_id,
            'invoice_policy':invoice_policy,'team_id':team_id,'client_order_ref':client_order_ref,
            'carrier_id':carrier_id,'invoice_shipping_on_delivery':invoice_shipping_on_delivery
            }
        """
        sale_order = self.env['sale.order']
        fpos = vals.get('fiscal_position_id',False)
        order_vals = {
            'company_id':vals.get('company_id'),
            'partner_id' :vals.get('partner_id'),
            'partner_invoice_id' : vals.get('partner_invoice_id'),
            'partner_shipping_id' : vals.get('partner_shipping_id'),
            'warehouse_id' : vals.get('warehouse_id'),
        }
        new_record = sale_order.new(order_vals)
        new_record.onchange_partner_id() # Return Pricelist- Payment terms- Invoice address- Delivery address
        order_vals = sale_order._convert_to_write({name: new_record[name] for name in new_record._cache})
        new_record = sale_order.new(order_vals)
        new_record.onchange_partner_shipping_id() # Return Fiscal Position
        order_vals = sale_order._convert_to_write({name: new_record[name] for name in new_record._cache})
        fpos = order_vals.get('fiscal_position_id',fpos)
        order_vals.update({
            'company_id':vals.get('company_id'),
            'picking_policy':vals.get('picking_policy'),
            'partner_invoice_id' : vals.get('partner_invoice_id'),
            'partner_id':vals.get('partner_id'),
            'date_order':vals.get('date_order',''),
            'state':'draft',
            'pricelist_id':vals.get('pricelist_id',''),
            'fiscal_position_id': fpos,
            'payment_term_id':vals.get('payment_term_id',''),
            'invoice_policy':vals.get('invoice_policy',''),
            'invoice_shipping_on_delivery':vals.get('invoice_shipping_on_delivery',False),
            'team_id':vals.get('team_id',''),
            'client_order_ref':vals.get('client_order_ref',''),
            'carrier_id':vals.get('carrier_id','')
            })
        return order_vals
        
