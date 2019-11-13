from odoo import models,fields,api
import requests

class woo_tags_ept(models.Model):
    _name="woo.tags.ept"
    _order='name'
    _description = "WooCommerce Product Tag"
    
    name=fields.Char("Name",required=1)
    description=fields.Text('Description')
    slug = fields.Char(string='Slug',help="The slug is the URL-friendly version of the name. It is usually all lowercase and contains only letters, numbers, and hyphens.")       
    woo_tag_id=fields.Integer("Woo Tag Id")    
    exported_in_woo=fields.Boolean("Exported In Woo",default=False)
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",required=1)

    @api.model
    def export_product_tags(self,instance,woo_product_tags):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()        
        for woo_product_tag in woo_product_tags:
            row_data = {'name': woo_product_tag.name,'description':str(woo_product_tag.description or '')}
            if woo_product_tag.slug:
                row_data.update({'slug':str(woo_product_tag.slug)})
            if instance.woo_version == 'old':
                data = {'product_tag':row_data}
            elif instance.woo_version == 'new':
                data = row_data
            res=wcapi.post("products/tags", data)
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Export Product Tags \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'tags',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if res.status_code not in [200,201]:
                if res.status_code == 500:
                    try:
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While export tag %s to WooCommerce for instance %s. \n%s"%(woo_product_tag.name,instance.name,e),
                             'mismatch_details':True,
                             'type':'tags',
                             'woo_instance_id':instance.id
                            })
                        continue
                    if isinstance(response,dict) and response.get('code')=='term_exists':
                        woo_product_tag.write({'woo_tag_id':response.get('data'),'exported_in_woo':True})
                        continue
                    else:                                            
                        message = res.content           
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'tags',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue            
            try:
                response = res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While export tag %s to WooCommerce for instance %s. \n%s"%(woo_product_tag.name,instance.name,e),
                     'mismatch_details':True,
                     'type':'tags',
                     'woo_instance_id':instance.id
                    })
                continue
            product_tag = False
            if instance.woo_version == 'old':            
                errors = response.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    message = "%s :: %s"%(message,woo_product_tag.name)
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'tags',
                                                 'woo_instance_id':instance.id
                                                })
                    continue    
                product_tag=response.get('product_tag',False)
            elif instance.woo_version == 'new':                
                product_tag=response
            product_tag_id= product_tag and product_tag.get('id',False)
            slug= product_tag and product_tag.get('slug','')
            if product_tag_id:
                woo_product_tag.write({'woo_tag_id':product_tag_id,'exported_in_woo':True,'slug':slug})
        return True
    
    @api.model
    def update_product_tags_in_woo(self,instance,woo_product_tags):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()
        for woo_tag in woo_product_tags:                                                               
            row_data = {'name':woo_tag.name,'description':str(woo_tag.description or '')}
            if woo_tag.slug:
                row_data.update({'slug':str(woo_tag.slug)})            
            if instance.woo_version == 'old':
                data = {"product_tag":row_data}
                res = wcapi.put('products/tags/%s'%(woo_tag.woo_tag_id),data)
            elif instance.woo_version == 'new':
                row_data.update({'id':woo_tag.woo_tag_id})
                res = wcapi.post('products/tags/batch',{'update':[row_data]})
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Get Product Tags \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'tags',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if res.status_code not in [200,201]:
                transaction_log_obj.create(
                                                {'message':res.content,
                                                 'mismatch_details':True,
                                                 'type':'tags',
                                                 'woo_instance_id':instance.id
                                                })
                continue           
            try:
                response = res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While update tag %s to WooCommerce for instance %s. \n%s"%(woo_tag.name,instance.name,e),
                     'mismatch_details':True,
                     'type':'tags',
                     'woo_instance_id':instance.id
                    })
                continue
            response_data = {}
            if not isinstance(response, dict):
                transaction_log_obj.create(
                                            {'message':"Response is not in proper format,Please Check Details",
                                             'mismatch_details':True,
                                             'type':'tags',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if instance.woo_version == 'old':
                errors = response.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'tags',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                else:
                    response_data = response.get('product_tags')
            else:
                response_data = response
            if response_data:
                woo_tag.write({'slug':response_data.get('slug') or response_data.get('update') and response_data.get('update')[0].get('slug')})                                
        return True
    
    def import_all_tags(self,wcapi,instance,transaction_log_obj,page):
        if instance.woo_version == 'old':
            res = wcapi.get("products/tags?filter[limit]=1000&page=%s"%(page))
        else:
            res = wcapi.get("products/tags?per_page=100&page=%s"%(page))
        if not isinstance(res,requests.models.Response):            
            transaction_log_obj.create({'message':"Get Product Tags \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'tags',
                                             'woo_instance_id':instance.id
                                            })
            return []
        if res.status_code not in [200,201]:
            transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'tags',
                                     'woo_instance_id':instance.id
                                    })
            return []
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import tags from WooCommerce for instance %s. \n%s"%(instance.name,e),
                 'mismatch_details':True,
                 'type':'tags',
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
                                             'type':'tags',
                                             'woo_instance_id':instance.id
                                            })
                return []
            return response.get('product_tags')
        elif instance.woo_version == 'new':            
            return response        
    
    @api.multi
    def sync_product_tags(self,instance,woo_product_tag=False):
        transaction_log_obj=self.env["woo.transaction.log"]
        wcapi = instance.connect_in_woo()
        if woo_product_tag and woo_product_tag.exported_in_woo:
            res = wcapi.get("products/tags/%s"%(woo_product_tag.woo_tag_id))
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Get Product Tags \nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'tags',
                                                 'woo_instance_id':instance.id
                                                })
                return True
            if res.status_code == 404:
                self.export_product_tags(instance, [woo_product_tag])
                return True
            if res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'tags',
                                     'woo_instance_id':instance.id
                                    })
                return True
            try:
                res = res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While import tag %s from WooCommerce for instance %s. \n%s"%(woo_product_tag.name,instance.name,e),
                     'mismatch_details':True,
                     'type':'tags',
                     'woo_instance_id':instance.id
                    })
                return False
            description = ''
            if instance.woo_version == 'old':
                description = res.get('product_tag',{}).get('description','')
            elif instance.woo_version == 'new':
                description = res.get('description')
            woo_product_tag.write({'description':description})
        else:
            if instance.woo_version == 'old':
                res = wcapi.get("products/tags?filter[limit]=1000")
            else:
                res = wcapi.get("products/tags?per_page=100")
            
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message':"Get Product Tags \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'tags',
                                             'woo_instance_id':instance.id
                                                })
                return True                
            if res.status_code  not in [200,201]:
                transaction_log_obj.create({'message':"Get Product Tags \nResponse is not in proper format :: %s"%(res.content),
                                                 'mismatch_details':True,
                                                 'type':'tags',
                                                 'woo_instance_id':instance.id
                                                })
                return True           
            results = []
            total_pages = res and res.headers.get('x-wp-totalpages',0) or 1
            try:
                res = res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While import tags from WooCommerce for instance %s. \n%s"%(instance.name,e),
                     'mismatch_details':True,
                     'type':'tags',
                     'woo_instance_id':instance.id
                    })
                return False
            
            if instance.woo_version == 'old':
                errors = res.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'tags',
                                                 'woo_instance_id':instance.id
                                                })
                    return True                
                results =  res.get('product_tags')                               
            elif instance.woo_version == 'new':                               
                results = res
            if int(total_pages) >=2:
                for page in range(2,int(total_pages)+1):            
                    results = results + self.import_all_tags(wcapi,instance,transaction_log_obj,page)
            
            for res in results:
                if not isinstance(res, dict):
                    continue
                tag_id = res.get('id')
                name= res.get('name')           
                description = res.get('description')
                slug = res.get('slug')
                woo_tag = self.search([('woo_tag_id','=',tag_id),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_tag:
                    woo_tag = self.search([('slug','=',slug),('woo_instance_id','=',instance.id)],limit=1)                    
                if woo_tag:
                    woo_tag.write({'woo_tag_id':tag_id,'name':name,'description':description,
                                   'slug':slug,'exported_in_woo':True})
                else:
                    self.create({'woo_tag_id':tag_id,'name':name,'description':description,
                                 'slug':slug,'woo_instance_id':instance.id,'exported_in_woo':True})
        return True