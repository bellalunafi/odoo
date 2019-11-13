from odoo import models,fields,api
from odoo.exceptions import Warning
import requests

class res_partner(models.Model):
    _inherit="res.partner"
    
    woo_company_name_ept=fields.Char("Woo Company Name")
    woo_customer_id=fields.Char("Woo Cutstomer Id")
    
    def import_all_woo_coustomers(self,wcapi,instance,transaction_log_obj,page):
        if instance.woo_version == 'new':
            res = wcapi.get('customers?per_page=100&page=%s'%(page))        
        else:
            res = wcapi.get('customers?filter[limit]=100&page=%s'%(page))
        if not isinstance(res,requests.models.Response):               
            transaction_log_obj.create({'message': "Import All Customers \nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'customer',
                                         'woo_instance_id':instance.id
                                        })
            return []
        if res.status_code not in [200,201]:
            message = "Error in Import All Customers %s"%(res.content)                        
            transaction_log_obj.create(
                                {'message':message,
                                 'mismatch_details':True,
                                 'type':'customer',
                                 'woo_instance_id':instance.id
                                })
            return []
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import Customers from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                         'mismatch_details':True,
                                         'type':'customer',
                                         'woo_instance_id':instance.id
                                        })
            return False
        if instance.woo_version == 'old':
            errors = response.get('errors','')
            if errors:
                message = errors[0].get('message')
                transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'customer',
                                             'woo_instance_id':instance.id
                                            })
                return
            return response.get('customers')
        elif instance.woo_version == 'new':
            return response
       
    @api.model
    def import_woo_customers(self,instance=False):        
        instances=[]
        transaction_log_obj=self.env["woo.transaction.log"]
        instances.append(instance)
        sale_order_obj=self.env['sale.order']
        
        for instance in instances:            
            wcapi = instance.connect_in_woo()
            if instance.woo_version == 'new':
                response = wcapi.get('customers?per_page=100')
            else:
                response = wcapi.get('customers?filter[limit]=-1')
            if not isinstance(response,requests.models.Response):                
                transaction_log_obj.create({'message': "Import Customers \nResponse is not in proper format :: %s"%(response),
                                             'mismatch_details':True,
                                             'type':'customer',
                                             'woo_instance_id':instance.id
                                            })
                continue                                    
            if response.status_code not in [200,201]:
                message = "Error in Import Customers %s"%(response.content)                        
                transaction_log_obj.create(
                                    {'message':message,
                                     'mismatch_details':True,
                                     'type':'customer',
                                     'woo_instance_id':instance.id
                                    })
                continue
            customer_ids = []
            if instance.woo_version=='old':
                try:
                    customer_ids = response.json().get('customers')
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import Customers from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                         'mismatch_details':True,
                                         'type':'customer',
                                         'woo_instance_id':instance.id
                                        })
                    continue
            else:
                try:
                    customer_response = response.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import Customers from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                         'mismatch_details':True,
                                         'type':'customer',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                customer_ids = customer_ids + customer_response
                total_pages = response.headers.get('X-WP-TotalPages')
                if int(total_pages) >=2:
                    for page in range(2,int(total_pages)+1):            
                        customer_ids = customer_ids + self.import_all_woo_coustomers(wcapi, instance, transaction_log_obj, page)
            
            billing = ''
            shipping = ''
            woo_customers = []
            
            if instance.woo_version == 'old':                
                woo_customers = customer_ids
                billing="billing_address"
                shipping="shipping_address"
            elif instance.woo_version == 'new':
                woo_customers = customer_ids
                billing="billing"
                shipping="shipping"
          
            for customer in woo_customers:
                woo_customer_id = customer.get('id',False)                
                partner=customer.get(billing,False) and sale_order_obj.create_or_update_woo_customer(woo_customer_id,customer.get(billing), False, False,False,instance)
                if partner:
                    customer.get(shipping,False) and sale_order_obj.create_or_update_woo_customer(False,customer.get(shipping),False,partner.id,'delivery',instance)