from odoo import models,fields,api
import requests

class woo_cancel_order_wizard(models.TransientModel):
    _name="woo.cancel.order.wizard"
    _description = "Woocommerce Cancel Order"
    
    @api.multi
    def get_amount(self):
        active_id=self._context.get('active_id')
        picking=self.env['stock.picking'].browse(active_id)        
        total=0.0
        for line in picking.move_lines:            
            total=total+line.sale_line_id.price_subtotal
        return total          

    message = fields.Char("Reason")
    amount=fields.Float("Amount",digits=(12,2))
    suggested_amount=fields.Float("Suggest Amount",digits=(12,2))
    journal_id=fields.Many2one('account.journal', 'Journal', help='You can select here the journal to use for the credit note that will be created. If you leave that field empty, it will use the same journal as the current invoice.')
    inv_line_des=fields.Char("Invoice Line Description",default="Refund Line")
    auto_create_refund=fields.Boolean("Auto Create Refund",default=True)
    company_id=fields.Many2one("res.company")
    date_ept=fields.Date("Invoice Date")
    
    def _get_active_picking(self):
        active_model = self._context.get('active_model')
        if  active_model == 'sale.order':
            active_id = self._context.get('active_id')
            sale_order = self.env[active_model].browse(active_id)
            return sale_order.picking_ids
        else:
            return False
    
    @api.model    
    def default_get(self,fields):
        res = super(woo_cancel_order_wizard, self).default_get(fields)
        if self._context.get('active_model') == 'sale.order':
            picking = self._get_active_picking()
            if not picking:
                return res           
            amount = self.with_context(active_id=picking[0].id).get_amount()
            res.update({'suggested_amount':amount,'amount':amount,'company_id':picking[0].company_id.id})
            return res
        active_id=self._context.get('active_id')
        picking=self.env['stock.picking'].browse(active_id)
        
        amount = self.get_amount()
        res.update({'suggested_amount':amount,'amount':amount,'company_id':picking.company_id.id})
        return res        

    """Cancel Order In Woo using this api we can not cancel partial order"""
    @api.multi
    def cancel_in_woo(self):
        transaction_log_obj=self.env["woo.transaction.log"]
        if self._context.get('active_model') == 'sale.order':
            picking = self._get_active_picking()
            active_id = picking[0].id
        else:    
            active_id=self._context.get('active_id')
        picking=self.env['stock.picking'].browse(active_id)
        instance=picking.woo_instance_id
        
        wcapi = instance.connect_in_woo()
        info = {'status': 'cancelled'}
        data = info
        if instance.woo_version == 'old':
            data = {'order':info}
            response = wcapi.put('orders/%s'%(picking.sale_id.woo_order_id),data)
        else:
            info.update({'id':picking.sale_id.woo_order_id})
            response = wcapi.post('orders/batch',{'update':[info]})
        if not isinstance(response,requests.models.Response):               
            transaction_log_obj.create({'message': "Cancel Order \nResponse is not in proper format :: %s"%(response),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
            return True
        if response.status_code not in [200,201]:
            transaction_log_obj.create(
                                {'message':"Error in Cancel Order %s"%(response.content),
                                 'mismatch_details':True,
                                 'type':'sales',
                                 'woo_instance_id':instance.id
                                })
            return True
        try:
            result = response.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While cancel order %s to WooCommerce for instance %s. \n%s"%(picking.sale_id.woo_order_id,instance.name,e),
                 'mismatch_details':True,
                 'type':'sales',
                 'woo_instance_id':instance.id
                })
            return False
        if instance.woo_version == 'old':
            errors = result.get('errors','')
            if errors:
                message = errors[0].get('message')
                transaction_log_obj.create(
                                            {'message':"Error in Cancel Order, %s"%(message),
                                             'mismatch_details':True,
                                             'type':'sales',
                                             'woo_instance_id':instance.id
                                            })
            else:
                if self.auto_create_refund:
                    self.create_refund(picking.sale_id, picking)
                picking.write({'canceled_in_woo':True})
        elif instance.woo_version == 'new':            
            if self.auto_create_refund:
                self.create_refund(picking.sale_id, picking)
            picking.write({'canceled_in_woo':True})              
        return True           

    @api.multi
    def create_refund(self,order,picking):
        account_invoice_line_obj=self.env['account.invoice.line']
        journal_id=self.journal_id and self.journal_id.id
        description = self.message or order.name
        
        source_invoice_id =False
        for line in order.order_line:
            for invoice_line in line.invoice_lines:
                source_invoice_id= invoice_line.invoice_id
                break
            
        invoice_vals = {
            'name':description,
            'origin': order.name,
            'type': 'out_refund',
            'reference': order.client_order_ref or order.name,
            'account_id': order.partner_id.property_account_receivable_id.id,
            'partner_id': order.partner_invoice_id.id,
            'journal_id': journal_id,
            'currency_id': order.pricelist_id.currency_id.id,
            'comment': order.note,
            'woo_instance_id':order.woo_instance_id.id,
            'payment_term_id': order.payment_term_id and order.payment_term_id.id or False,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self._uid or False,
            'date_invoice':self.date_ept or False,
            'team_id' : order.team_id and order.team_id.id,
            'source_invoice_id': source_invoice_id and source_invoice_id.id or False,            
#             'picking_id':picking.id
        }
        invoice=self.env['account.invoice'].create(invoice_vals)
        partner_id=order.partner_invoice_id.id
        fiscal_position=order.fiscal_position_id.id or order.partner_id.property_account_position_id.id
        currency_id=order.pricelist_id.currency_id.id
        tax_ids=[]
        product=False
        qty=0.0
        for line in picking.move_lines:
            if not product:
                product=line.product_id
            tax_ids+=line.sale_line_id.tax_id.ids
            qty+=line.product_qty
        tax_ids=list(set(tax_ids))
        uos_id=False
        account_id=product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id
        
        price_unit = round(self.amount/ qty,self.env['decimal.precision'].precision_get('Product Price'))

        vals = ({'invoice_line_tax_ids':[(6,0,tax_ids)],'invoice_id':invoice.id,'product_id':False,'price_unit':price_unit,'quantity':qty,'name':self.inv_line_des,'account_id':account_id})
        account_invoice_line_obj.create(vals)

        return True