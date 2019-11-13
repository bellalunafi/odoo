from odoo import models,fields,api
import requests

class woo_payment_gateway(models.Model):
    _name="woo.payment.gateway"
    _description = "Payment Gateway"
    
    name=fields.Char("Payment Method", required=True)
    code=fields.Char("Payment Code", required=True,help="The payment code should match Gateway ID in your WooCommerce Checkout Settings.")
    woo_instance_id=fields.Many2one("woo.instance.ept",string="Instance",required=True)
    _sql_constraints=[('_payment_gateway_unique_constraint','unique(code,woo_instance_id)',"Payment gateway code must be unique in the list")]
    
    @api.multi
    def get_payment_gateway(self,instance):
        transaction_log_obj=self.env['woo.transaction.log']
        payment_gateway_obj=self.env['woo.payment.gateway']
        wcapi = instance.connect_in_woo()
        res = wcapi.get("payment_gateways")
        if not isinstance(res,requests.models.Response):                
            transaction_log_obj.create({'message':"Import Payment Gateway \nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
            return False
        if res.status_code not in [200,201]:
            message = res.content           
            if message:
                transaction_log_obj.create(
                                            {'message':"Import Payment Gateway Error, %s"%(message),
                                             'mismatch_details':True,
                                             'type':'sales',
                                             'woo_instance_id':instance.id
                                            })
                return False
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import payment gateways from WooCommerce for instance %s. \n%s"%(instance.name,e),
                         'mismatch_details':True,
                         'type':'sales',
                         'woo_instance_id':instance.id
                        })
            return False
        for payment_method in response:
            if payment_method.get('enabled'):
                name=payment_method.get('title')
                code=payment_method.get('id')
                existing_payment_gateway = payment_gateway_obj.search([('code','=',code),('woo_instance_id','=',instance.id)])
                if existing_payment_gateway or not name or not code:
                    continue
                payment_gateway_obj.create({'name':name,'code':code,'woo_instance_id':instance.id})