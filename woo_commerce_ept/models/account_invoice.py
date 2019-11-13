from odoo import models,fields,api
from .. import woocommerce
import requests
   
class account_invoice(models.Model):
    _inherit="account.invoice"
    
    woo_instance_id=fields.Many2one("woo.instance.ept","Woo Instances")
    is_refund_in_woo=fields.Boolean("Refund In Woo Commerce",default=False)
    source_invoice_id = fields.Many2one('account.invoice','Source Invoice')
    
    @api.multi
    def refund_in_woo(self):
        transaction_log_obj=self.env['woo.transaction.log']
        for refund in self:
            if not refund.woo_instance_id:
                continue
            wcapi = refund.woo_instance_id.connect_in_woo()
            orders = []
            if refund.source_invoice_id:
                lines=self.env['sale.order.line'].search([('invoice_lines.invoice_id','=',refund.source_invoice_id.id)])
                order_ids=[line.order_id.id for line in lines]
                orders=order_ids and self.env['sale.order'].browse(list(set(order_ids))) or []                
                    
            for order in orders:
                data = {'amount':str(refund.amount_total),'reason':str(refund.name or '')}
                if refund.woo_instance_id.woo_version == 'old':
                    response = wcapi.post('orders/%s/refunds'%(order.woo_order_id),{'order_refund':data})
                elif refund.woo_instance_id.woo_version == 'new':
                    response = wcapi.post('orders/%s/refunds'%(order.woo_order_id),data)
                if not isinstance(response,requests.models.Response):
                    transaction_log_obj.create({'message':"Refund \n Response is not in proper format :: %s"%(response),
                                                 'mismatch_details':True,
                                                 'type':'sales',
                                                 'woo_instance_id':refund.woo_instance_id.id
                                                })
                    continue
                if response.status_code not in [200,201]:
                    transaction_log_obj.create(
                                        {'message':"Refund \n%s"%(response.content),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':refund.woo_instance_id.id
                                        })
                    continue
                try:
                    response = response.json()
                except Exception as e:
                    transaction_log_obj.create(
                                        {'message':"Json Error : While refunding Order %s to WooCommerce for instance %s. \n%s"%(refund.woo_instance_id.name,order.woo_order_id,e),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':refund.woo_instance_id.id
                                        })
                    continue
            orders and refund.write({'is_refund_in_woo':True})
        return True

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(account_invoice,self)._prepare_refund(invoice,date_invoice = date_invoice, date=date, description=description, journal_id=journal_id)
        if invoice.woo_instance_id:
            values.update({'woo_instance_id':invoice.woo_instance_id.id,'source_invoice_id':invoice.id})        
        return values    

class sale_order(models.Model):
    _inherit="sale.order"
 
    def _prepare_invoice(self):    
        inv_id=super(sale_order,self)._prepare_invoice()
        if inv_id and self.woo_instance_id:            
            inv_id.update({'woo_instance_id':self.woo_instance_id.id})
        return inv_id