from odoo import models,api,fields
import requests
from odoo.exceptions import Warning

class WooCoupons(models.Model):
    _name="woo.coupons.ept"
    _rec_name="code"
    _description="WooCommerce Coupon"
   
    coupon_id = fields.Integer("WooCommerce Id")
    code = fields.Char("Code",required=1)
    description = fields.Text('Description')
    discount_type = fields.Selection([('fixed_cart','Cart Discount'),
                           ('percent','Cart % Discount'),
                           ('fixed_product','Product Discount'),
                           ('percent_product','Product % Discount')
                           ],"Discount Type",default="fixed_cart")
    amount = fields.Float("Amount")
    free_shipping = fields.Boolean("Allow Free Shipping",help="Check this box if the coupon grants free shipping. A free shipping method must be enabled in your shipping zone and be set to require \"a valid free shipping coupon\" (see the \"Free Shipping Requires\" setting in WooCommerce).")
    expiry_date = fields.Date("Expiry Date")
    minimum_amount = fields.Float("Minimum Spend")
    maximum_amount = fields.Float("Maximum Spend")
    individual_use = fields.Boolean("Individual Use",help="Check this box if the coupon cannot be used in conjunction with other coupons.")
    exclude_sale_items = fields.Boolean("Exclude Sale Items",help="Check this box if the coupon should not apply to items on sale. Per-item coupons will only work if the item is not on sale. Per-cart coupons will only work if there are no sale items in the cart.")
    product_ids = fields.Many2many("woo.product.template.ept",'woo_product_tmpl_product_rel','product_ids','woo_product_ids',"Products")
    exclude_product_ids = fields.Many2many("woo.product.template.ept",'woo_product_tmpl_exclude_product_rel','exclude_product_ids','woo_product_ids',"Exclude Products")
    product_category_ids = fields.Many2many('woo.product.categ.ept','woo_template_categ_incateg_rel','product_category_ids','woo_categ_id',"Product Categories")
    excluded_product_category_ids = fields.Many2many('woo.product.categ.ept','woo_template_categ_exclude_categ_rel','excluded_product_category_ids','woo_categ_id',"Exclude Product Categories")
    email_restrictions = fields.Char("Email restrictions",help="List of email addresses that can use this coupon, Enter Email ids Sepreated by comma(,)",default="")
    usage_limit = fields.Integer("Usage limit per coupon")
    limit_usage_to_x_items = fields.Integer("Limit usage to X items")
    usage_limit_per_user = fields.Integer("Usage limit per user")
    usage_count=fields.Integer("Usage Count")
    date_created=fields.Datetime("Created Date")
    date_modified=fields.Datetime("Modified Date")
    used_by = fields.Char("Used By")
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",required=1)
    exported_in_woo = fields.Boolean("Exported in WooCommerce")
    _sql_constraints = [('code_unique', 'unique(code,woo_instance_id)', "Code is already exists. Code must be unique!")]
         
    
    """using this method we checking that is their any same value in product and exclude product same for category"""
    @api.model
    def create(self, vals):
        if vals.get("product_ids"):
            for val in vals.get("product_ids")[0][2]:
                if vals.get("exclude_product_ids"):
                    if val in vals.get("exclude_product_ids")[0][2]: 
                        raise Warning("Same Product will not allowed to select in both Products and Exclude Products")
        if vals.get("product_category_ids"):
            for val in vals.get("product_category_ids")[0][2]:
                if vals.get("excluded_product_category_ids"):
                    if val in vals.get("excluded_product_category_ids")[0][2]: 
                        raise Warning("Same Product Category will not allowed to select in both Products and Exclude Products")
        return super(WooCoupons,self).create(vals)
   
    """using this method we checking that is their any same value in product and exclude product same for category"""
    @api.multi
    def write(self,vals):
        if vals.get("product_ids"):
            for val in vals.get("product_ids")[0][2]:
                if vals.get("exclude_product_ids"):
                    if val in vals.get("exclude_product_ids")[0][2]: 
                        raise Warning("Same Product will not allowed to select in both Products and Exclude Products")
        if vals.get("product_category_ids"):
            for val in vals.get("product_category_ids")[0][2]:
                if vals.get("excluded_product_category_ids"):
                    if val in vals.get("excluded_product_category_ids")[0][2]: 
                        raise Warning("Same Product Category will not allowed to select in both Products and Exclude Products")
        return super(WooCoupons,self).write(vals)
   
    """this method is used to create coupon from Odoo to WooCommerce and store response data"""    
    @api.model
    def export_coupons(self,instance,woo_coupons):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()       

        for woo_coupon in woo_coupons:
            
            woo_product_tmpl_ids=[]
            woo_product_exclude_tmpl_ids=[]
            woo_category_ids=[]
            woo_exclude_category_ids=[]
            
            for product_tmpl_id in woo_coupon.product_ids:
                woo_product_tmpl_ids.append(product_tmpl_id.woo_tmpl_id)
            
            for exclude_product_tmpl_id in woo_coupon.exclude_product_ids:
                woo_product_exclude_tmpl_ids.append(exclude_product_tmpl_id.woo_tmpl_id)
            
            for categ_id in woo_coupon.product_category_ids:
                woo_category_ids.append(categ_id.woo_categ_id)
            
            for exclude_categ_id in woo_coupon.excluded_product_category_ids:
                woo_exclude_category_ids.append(exclude_categ_id.woo_categ_id)
            
            free_shipping="free_shipping"
            prodcut_category = "product_categories"
            exclude_prodcut_category = "excluded_product_categories"
            email_restriction = "email_restrictions"
            discount_type = "discount_type"
            if instance.woo_version == 'old':
                free_shipping = "enable_free_shipping"
                prodcut_category = "product_category_ids"
                exclude_prodcut_category = "exclude_product_category_ids"
                email_restriction = "customer_emails"
                discount_type = "type"
            
            email_ids = []
            if woo_coupon.email_restrictions:
                email_ids = woo_coupon.email_restrictions.split(",")
            
            row_data = {'code': woo_coupon.code,
                        'description':str(woo_coupon.description or '') or '',
                        discount_type: woo_coupon.discount_type,
                        free_shipping:woo_coupon.free_shipping,
                        'amount': str(woo_coupon.amount),
                        'expiry_date'if not instance.is_latest else 'date_expires':"{}".format(woo_coupon.expiry_date or ''),
                        'minimum_amount':str(woo_coupon.minimum_amount),
                        'maximum_amount':str(woo_coupon.maximum_amount),
                        'individual_use':woo_coupon.individual_use,
                        'exclude_sale_items':woo_coupon.exclude_sale_items,
                        'product_ids':woo_product_tmpl_ids,
                        'exclude_product_ids'if not instance.is_latest else 'excluded_product_ids':woo_product_exclude_tmpl_ids,
                        prodcut_category:woo_category_ids,
                        exclude_prodcut_category:woo_exclude_category_ids,
                        email_restriction:email_ids,
                        'usage_limit':woo_coupon.usage_limit,
                        'limit_usage_to_x_items':woo_coupon.limit_usage_to_x_items,
                        'usage_limit_per_user':woo_coupon.usage_limit_per_user,
                        }
           
            if instance.woo_version == 'old':
                data = {'coupon':row_data}
            elif instance.woo_version == 'new':
                data = row_data
            
            res = wcapi.post("coupons", data)
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Export Coupons \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'coupon',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if res.status_code not in [200,201]:
                message = res.content           
                if message:
                    transaction_log_obj.create(
                                                {'message':"Can not Export Coupons, %s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'coupon',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if instance.woo_version == 'old':
                    try:
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While export coupon %s to WooCommerce for instance %s. \n%s"%(woo_coupon.code,instance.name,e),
                                     'mismatch_details':True,
                                     'type':'coupon',
                                     'woo_instance_id':instance.id
                                    })
                        continue            
                    errors = response.get('errors','')
                    if errors:
                        message = errors[0].get('message')
                        transaction_log_obj.create(
                                                    {'message':"Can not Export Coupons,  %s"%(message),
                                                     'mismatch_details':True,
                                                     'type':'coupon',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                                
            if instance.woo_version == 'new':
                try:
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While export coupon %s to WooCommerce for instance %s. \n%s"%(woo_coupon.code,instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    continue
                woo_coupon.write({"coupon_id":response.get("id"),"used_by":response.get("used_by"),"date_created":response.get("date_created"),"date_modified":response.get("date_modified"),"exported_in_woo":True})
        
            if instance.woo_version == 'old':
                try:
                    response = res.json().get("coupon")
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While export coupon %s to WooCommerce for instance %s. \n%s"%(woo_coupon.code,instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    continue
                woo_coupon.write({"coupon_id":response.get("id"),"date_created":response.get("created_at"),"date_modified":response.get("updated_at"),"exported_in_woo":True})
               
        return True
    
    """this method is used to create coupon from Odoo to WooCommerce and store response data"""    
    @api.model
    def update_coupons(self,instance,woo_coupons):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()       

        for woo_coupon in woo_coupons:
            if woo_coupon.coupon_id == 0 and not woo_coupon.exported_in_woo:    
                raise Warning("Coupon is not having coupon id or not exported in WooCommerce")
            
            woo_product_tmpl_ids=[]
            woo_product_exclude_tmpl_ids=[]
            woo_category_ids=[]
            woo_exclude_category_ids=[]
            
            for product_tmpl_id in woo_coupon.product_ids:
                woo_product_tmpl_ids.append(product_tmpl_id.woo_tmpl_id)
            
            for exclude_product_tmpl_id in woo_coupon.exclude_product_ids:
                woo_product_exclude_tmpl_ids.append(exclude_product_tmpl_id.woo_tmpl_id)
            
            for categ_id in woo_coupon.product_category_ids:
                woo_category_ids.append(categ_id.woo_categ_id)
            
            for exclude_categ_id in woo_coupon.excluded_product_category_ids:
                woo_exclude_category_ids.append(exclude_categ_id.woo_categ_id)
            
            free_shipping="free_shipping"
            prodcut_category = "product_categories"
            exclude_prodcut_category = "excluded_product_categories"
            email_restriction = "email_restrictions"
            discount_type = "discount_type"
            if instance.woo_version == 'old':
                free_shipping = "enable_free_shipping"
                prodcut_category = "product_category_ids"
                exclude_prodcut_category = "exclude_product_category_ids"
                email_restriction = "customer_emails"
                discount_type = "type"
            
            email_ids = []
            if woo_coupon.email_restrictions:
                email_ids = woo_coupon.email_restrictions.split(",")
            
            row_data = {'code': woo_coupon.code,
                        'description':str(woo_coupon.description or '') or '',
                        discount_type: woo_coupon.discount_type,
                        free_shipping:woo_coupon.free_shipping,
                        'amount': str(woo_coupon.amount),
                        'expiry_date'if not instance.is_latest else 'date_expires':"{}".format(woo_coupon.expiry_date or ''),
                        'minimum_amount':str(woo_coupon.minimum_amount),
                        'maximum_amount':str(woo_coupon.maximum_amount),
                        'individual_use':woo_coupon.individual_use,
                        'exclude_sale_items':woo_coupon.exclude_sale_items,
                        'product_ids':woo_product_tmpl_ids,
                        'exclude_product_ids'if not instance.is_latest else 'excluded_product_ids':woo_product_exclude_tmpl_ids,
                        prodcut_category:woo_category_ids,
                        exclude_prodcut_category:woo_exclude_category_ids,
                        email_restriction:email_ids,
                        'usage_limit':woo_coupon.usage_limit,
                        'limit_usage_to_x_items':woo_coupon.limit_usage_to_x_items,
                        'usage_limit_per_user':woo_coupon.usage_limit_per_user,
                        }
         
            if instance.woo_version == 'old':
                data = {'coupon':row_data}
                res = wcapi.put("coupons/"+str(woo_coupon.coupon_id),data)
            elif instance.woo_version == 'new':
                row_data.update({'id':woo_coupon.coupon_id})
                res = wcapi.post("coupons/batch",{'update':[row_data]})
                
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Export Coupons \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'coupon',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if res.status_code not in [200,201]:
                if res.status_code == 500:
                    try:
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While update coupon %s to WooCommerce for instance %s. \n%s"%(woo_coupon.code,instance.name,e),
                                     'mismatch_details':True,
                                     'type':'coupon',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    if isinstance(response,dict) and response.get('code')=='term_exists':
                        woo_coupon.write({'code':response.get('code'),'exported_in_woo':True})
                        continue
                if instance.woo_version == 'old':
                    try:
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While update coupon %s to WooCommerce for instance %s. \n%s"%(woo_coupon.code,instance.name,e),
                                     'mismatch_details':True,
                                     'type':'coupon',
                                     'woo_instance_id':instance.id
                                    })
                        continue            
                    errors = response.get('errors')
                    if errors:
                        message = errors[0].get('message')
                        transaction_log_obj.create(
                                                    {'message':"Can not Export Coupons,  %s"%(message),
                                                     'mismatch_details':True,
                                                     'type':'coupon',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                else:                                            
                    message = res.content
                    try:
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While update coupon %s to WooCommerce for instance %s. \n%s "%(woo_coupon.code,instance.name,e),
                                     'mismatch_details':True,
                                     'type':'coupon',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    if instance.woo_version == 'new':
                        if res.json().get("code") == "woocommerce_rest_shop_coupon_invalid_id":
                            message = "Coupon ID %s is Invalid or Not exists in WooCommerce"%woo_coupon.coupon_id           
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'coupon',
                                                 'woo_instance_id':instance.id
                                                })
                    continue   
                    
            if instance.woo_version == 'new':
                try:
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update coupon %s to WooCommerce for instance %s. \n%s"%(woo_coupon.code,instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    continue
                woo_coupon.write({"coupon_id":response.get("id"),"used_by":response.get("used_by"),"date_created":response.get("date_created"),"date_modified":response.get("date_modified"),"exported_in_woo":True})
        
            if instance.woo_version == 'old':
                try:
                    response = res.json().get("coupon")
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update coupon %s to WooCommerce for instance %s. \n%s"%(woo_coupon.code,instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    continue
                woo_coupon.write({"coupon_id":response.get("id"),"date_created":response.get("created_at"),"date_modified":response.get("updated_at"),"exported_in_woo":True})
        return True
    
    """This method will create or update coupon"""
    @api.multi
    def create_or_write_coupon(self,instance,coupons):
        
        woo_product_categ_ept_obj = self.env["woo.product.categ.ept"]
        woo_product_template_ept_obj = self.env["woo.product.template.ept"]
        coupon = ""
        expiry_date = False
        for coupon in coupons:    
            coupon_id = coupon.get("id")
            code = coupon.get("code")
            if instance.woo_version == 'new':
                free_shipping=coupon.get("free_shipping")
                woo_product_categ = woo_product_categ_ept_obj.search([("woo_categ_id","in",coupon.get("product_categories")),("woo_instance_id","=",instance.id)]).ids                 
                prodcut_category = [(6, False, woo_product_categ)] or '' 
                exclude_woo_product_categ = woo_product_categ_ept_obj.search([("woo_categ_id","in",coupon.get("excluded_product_categories")),("woo_instance_id","=",instance.id)]).ids
                exclude_prodcut_category = [(6, False, exclude_woo_product_categ)] or ''
                email_restriction = coupon.get("email_restrictions") or ''
                discount_type = coupon.get("discount_type")
            if instance.woo_version == 'old':
                free_shipping = coupon.get("enable_free_shipping")
                woo_product_categ = woo_product_categ_ept_obj.search([("woo_categ_id","in",coupon.get("product_category_ids")),("woo_instance_id","=",instance.id)]).ids
                prodcut_category = [(6, False, woo_product_categ)] or '' 
                exclude_woo_product_categ = woo_product_categ_ept_obj.search([("woo_categ_id","in",coupon.get("exclude_product_category_ids")),("woo_instance_id","=",instance.id)]).ids
                exclude_prodcut_category = [(6, False, exclude_woo_product_categ)] or ''
                email_restriction = coupon.get("customer_emails") or ''
                discount_type = coupon.get("type")
                
            woo_coupon = self.search(["&","|",('coupon_id','=',coupon_id),('code','=',code),('woo_instance_id','=',instance.id)],limit=1)
            
            woo_product_ids = woo_product_template_ept_obj.search([("woo_tmpl_id","in",coupon.get("product_ids")),("woo_instance_id","=",instance.id)]).ids
            if not instance.is_latest:
                exclude_woo_product_ids = woo_product_template_ept_obj.search([("woo_tmpl_id","in",coupon.get("exclude_product_ids")),("woo_instance_id","=",instance.id)]).ids
                expiry_date = coupon.get("expiry_date") and coupon.get("expiry_date") or False
            else:
                exclude_woo_product_ids = woo_product_template_ept_obj.search([("woo_tmpl_id","in",coupon.get("excluded_product_ids")),("woo_instance_id","=",instance.id)]).ids
                expiry_date = coupon.get("date_expires") and coupon.get("date_expires") or False
                
            email_ids = ""
            
            if email_restriction:
                email_ids = ",".join(email_restriction)
                        
            vals = {
                'coupon_id': coupon_id, 
                'code' : code,
                'description' : coupon.get("description"),
                'discount_type' : discount_type,
                'amount' : coupon.get("amount"),
                'free_shipping' : free_shipping,
                'expiry_date' : expiry_date,
                'minimum_amount' : float(coupon.get("minimum_amount",0.0)),
                'maximum_amount' : float(coupon.get("minimum_amount",0.0)),
                'individual_use' : coupon.get("individual_use"),
                'exclude_sale_items' : coupon.get("exclude_sale_items"),
                'product_ids' : [(6, False, woo_product_ids)] or '',
                'exclude_product_ids' : [(6, False, exclude_woo_product_ids)] or '',
                'product_category_ids' : prodcut_category or '',
                'excluded_product_category_ids' : exclude_prodcut_category or '',
                'email_restrictions' : email_ids,
                'usage_limit' : coupon.get("usage_limit"),
                'limit_usage_to_x_items' : coupon.get("limit_usage_to_x_items"),
                'usage_limit_per_user' : coupon.get("usage_limit_per_user"),
                'usage_count' : coupon.get("usage_count"),
                'date_created' : coupon.get("date_created"),
                'date_modified' : coupon.get("date_modified"),
                'used_by' : coupon.get("used_by"),
                'woo_instance_id' : instance.id,
                'exported_in_woo' : True
            }
            
            if not woo_coupon:
                self.create(vals)
            else:
                woo_coupon.write(vals)
    
    def import_all_woo_coupons(self,wcapi,instance,transaction_log_obj,page):
        if instance.woo_version == 'new':
            res = wcapi.get('coupons?per_page=100&page=%s'%(page))        
        else:
            res = wcapi.get('coupons?filter[limit]=1000&page=%s'%(page))
        if not isinstance(res,requests.models.Response):               
            transaction_log_obj.create({'message': "Import All Coupons \nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'coupon',
                                         'woo_instance_id':instance.id
                                        })
            return []
        if res.status_code not in [200,201]:
            message = "Error in Import All Coupons %s"%(res.content)                        
            transaction_log_obj.create(
                                {'message':message,
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
            return []
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import coupons from WooCommerce for instance %s. \n%s"%(instance.name,e),
                         'mismatch_details':True,
                         'type':'coupon',
                         'woo_instance_id':instance.id
                        })
            return []
        if instance.woo_version == 'old':
            errors = response.get('errors','')
            if errors:
                message = errors[0].get('message')
                transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'coupon',
                                             'woo_instance_id':instance.id
                                            })
                return []
            return response.get('coupons')
        elif instance.woo_version == 'new':
            return response
    
    @api.multi
    def sync_coupons(self,instance,woo_coupons=False):
        transaction_log_obj=self.env["woo.transaction.log"]
        wcapi = instance.connect_in_woo()
        coupon_ids=[]
        if woo_coupons and woo_coupons.exported_in_woo:
            if instance.woo_version == 'old':
                res = wcapi.get("coupons?filter[limit]=-1")
            else:
                res = wcapi.get("coupons?per_page=100")
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Get Coupons \nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'coupon',
                                                 'woo_instance_id':instance.id
                                                })
                return True
            if res.status_code == 404:
                self.export_coupons(instance, [woo_coupons])
                return True
            if res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'coupon',
                                     'woo_instance_id':instance.id
                                    })
                return True
            if instance.woo_version == 'old':
                try:
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import coupons from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    return False            
                errors = response.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':"Can not Export Coupons,  %s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'coupon',
                                                 'woo_instance_id':instance.id
                                                })
                    return True
            
            if instance.woo_version == 'old':
                try:
                    coupon_ids = res.json().get("coupons")
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import coupons from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    return False
            else:
                try:
                    coupon_response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import coupons from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    return False
                coupon_ids = coupon_ids + coupon_response
                total_pages = res.headers.get('x-wp-totalpages',0)
                if int(total_pages) >=2:
                    for page in range(2,int(total_pages)+1):            
                        coupon_ids = coupon_ids + self.import_all_woo_coupons(wcapi,instance,transaction_log_obj,page)
            
            self.create_or_write_coupon(instance, coupon_ids)
        else:
            if instance.woo_version == 'old':
                res = wcapi.get("coupons?filter[limit]=-1")
            else:
                res = wcapi.get("coupons?per_page=100")
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Get Coupons \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'coupon',
                                             'woo_instance_id':instance.id
                                                })
                return True                
            if res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'coupon',
                                     'woo_instance_id':instance.id
                                    })
                return True 
            if instance.woo_version == 'old':
                try:
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import coupons from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    return False            
                errors = response.get('errors')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':"Can not Export Coupons,  %s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'coupon',
                                                 'woo_instance_id':instance.id
                                                })
                    return True 
            
            coupon_response = ""
            if instance.woo_version == 'old':
                try:
                    coupon_ids = res.json().get("coupons")
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import coupons from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    return False
            else:
                try:
                    coupon_response=res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import coupons from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'coupon',
                                 'woo_instance_id':instance.id
                                })
                    return False
                coupon_ids = coupon_ids + coupon_response
                total_pages = res.headers.get('x-wp-totalpages',0)
                if int(total_pages) >=2:
                    for page in range(2,int(total_pages)+1):            
                        coupon_ids = coupon_ids + self.import_all_woo_coupons(wcapi,instance,transaction_log_obj,page)         
            self.create_or_write_coupon(instance, coupon_ids)
        return True