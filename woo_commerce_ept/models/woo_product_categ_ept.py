from odoo import models,fields,api,_
from .. img_upload import img_file_upload
import base64
import requests
from odoo.exceptions import ValidationError
import sys
import importlib
importlib.reload(sys)
PYTHONIOENCODING="UTF-8"

class woo_product_categ_ept(models.Model):
    _name='woo.product.categ.ept'
    _order='name'
    _description = "WooCommerce Product Category"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _rec_name = 'complete_name'
    
    @api.one
    def set_image(self):
        for categ_image in self:
            if categ_image.woo_instance_id.is_image_url:
                if categ_image.response_url:          
                    try:                     
                        img = requests.get(categ_image.response_url,stream=True,verify=False,timeout=10)
                        if img.status_code == 200:
                            categ_image.url_image_id=base64.b64encode(img.content)
                        else:
                            img = requests.get(categ_image.url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:
                                categ_image.url_image_id=base64.b64encode(img.content)
                    except Exception:
                        try:                     
                            img = requests.get(categ_image.url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:
                                categ_image.url_image_id=base64.b64encode(img.content)
                        except Exception:
                            pass
                elif categ_image.url:
                    try:                     
                        img = requests.get(categ_image.url,stream=True,verify=False,timeout=10)
                        if img.status_code == 200:
                            categ_image.url_image_id=base64.b64encode(img.content)
                    except Exception:
                        pass            
    
    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))
        return True
    
    name=fields.Char('Name', required="1",translate=True)
    parent_id=fields.Many2one('woo.product.categ.ept', string='Parent',index=True, ondelete='cascade')
    description=fields.Char('Description',translate=True)
    slug = fields.Char(string='Slug',help="The slug is the URL-friendly version of the name. It is usually all lowercase and contains only letters, numbers, and hyphens.")
    display=fields.Selection([('default','Default'),
                                ('products','Products'),
                                ('subcategories','Sub Categories'),
                                ('both','Both') 
                                ],default='default')
    is_image_url=fields.Boolean("Is Image Url ?",related="woo_instance_id.is_image_url")
    image=fields.Binary('Image')
    url = fields.Char(size=600, string='Image URL')
    response_url = fields.Char(size=600, string='Response URL',help="URL from WooCommerce")
    url_image_id=fields.Binary("URL Image",compute=set_image,store=False)    
    woo_categ_id=fields.Integer('Woo Category Id', readonly=True)
    parent_left = fields.Integer('Left Parent', index=1)
    parent_right = fields.Integer('Right Parent', index=1)
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",required=1)
    exported_in_woo=fields.Boolean('Exported In Woo', default=False, readonly=True)  
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name')
    parent_path = fields.Char(index=True) #Field Added by Jay Makwana 22/11/18  
    
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name
    
    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]
    
    @api.multi
    def export_product_categs(self,instance,woo_product_categs):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()        
        for woo_product_categ in woo_product_categs:
            if woo_product_categ.woo_categ_id:
                res = wcapi.get("products/categories/%s"%(woo_product_categ.woo_categ_id))
                if not isinstance(res,requests.models.Response):
                    transaction_log_obj.create({'message':"Get Product Category \nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'category',
                                                 'woo_instance_id':instance.id
                                                })
                    continue                                    
                if res.status_code != 404:
                    continue
                if res.status_code not in [200,201]:
                    transaction_log_obj.create(
                                        {'message':res.content,
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
                    continue
            product_categs=[]
            product_categs.append(woo_product_categ)
            for categ in product_categs:
                if categ.parent_id and categ.parent_id not in product_categs and not categ.parent_id.woo_categ_id:
                    product_categs.append(categ.parent_id)
                    
            product_categs.reverse()
            for woo_product_categ in product_categs:                
                img_url = ''
                if instance.is_image_url:
                    if woo_product_categ.response_url:
                        try:
                            img = requests.get(woo_product_categ.response_url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:                                
                                img_url = woo_product_categ.response_url
                            elif woo_product_categ.url:
                                img_url = woo_product_categ.url
                        except Exception:
                            img_url = woo_product_categ.url or ''
                    elif woo_product_categ.url:
                        img_url = woo_product_categ.url
                else:
                    res = {}            
                    if woo_product_categ.image:
                        res = img_file_upload.upload_image(instance,woo_product_categ.image,"%s_%s"%(woo_product_categ.name,woo_product_categ.id))
                    img_url = res and res.get('url',False) or ''
                row_data = {'name': str(woo_product_categ.name),
                                           'description':str(woo_product_categ.description or ''),                                           
                                           'display':str(woo_product_categ.display),
                                           }
                if woo_product_categ.slug:
                    row_data.update({'slug':str(woo_product_categ.slug)})
                img_url and row_data.update({'image' :img_url})
                if instance.woo_version == 'new' and img_url:
                    row_data.update({'image' :{'src':img_url}})
                woo_product_categ.parent_id.woo_categ_id and row_data.update({'parent':woo_product_categ.parent_id.woo_categ_id})   
                if instance.woo_version == 'old':                
                    data = {'product_category':row_data}                    
                elif instance.woo_version == 'new':
                    data = row_data
                res=wcapi.post("products/categories", data)
                if not isinstance(res,requests.models.Response):
                    transaction_log_obj.create({'message':"Export Product Category \nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'category',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if res.status_code not in [200,201]:
                    if res.status_code == 500:
                        try:
                            response = res.json()
                        except Exception as e:
                            transaction_log_obj.create({'message':"Json Error : While export product category %s to WooCommerce for instance %s. \n%s"%(woo_product_categ.name,instance.name,e),
                                 'mismatch_details':True,
                                 'type':'category',
                                 'woo_instance_id':instance.id
                                })
                            continue
                        if isinstance(response,dict) and response.get('code')=='term_exists':
                            woo_product_categ.write({'woo_categ_id':response.get('data'),'exported_in_woo':True})
                            continue
                        else:                                            
                            message = res.content           
                            transaction_log_obj.create(
                                                        {'message':message,
                                                         'mismatch_details':True,
                                                         'type':'category',
                                                         'woo_instance_id':instance.id
                                                        })
                            continue
                try:
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While export product category %s to WooCommerce for instance %s. \n%s"%(woo_product_categ.name,instance.name,e),
                         'mismatch_details':True,
                         'type':'category',
                         'woo_instance_id':instance.id
                        })
                    continue
                if not isinstance(response,dict):
                    transaction_log_obj.create({'message':"Export Product Category \nResponse is not in proper format :: %s"%(response),
                                                 'mismatch_details':True,
                                                 'type':'category',
                                                 'woo_instance_id':instance.id
                                                })
                    continue 
                if instance.woo_version == 'old':                
                    errors = response.get('errors','')
                    if errors:
                        message = errors[0].get('message')
                        message = "%s :: %s"%(message,woo_product_categ.name)
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'category',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                    product_categ=response.get('product_category',False)
                elif instance.woo_version == 'new':
                    product_categ=response
                product_categ_id = product_categ and product_categ.get('id',False)
                slug = product_categ and product_categ.get('slug','')
                response_data = {}
                if instance.is_image_url:
                    response_url = ''
                    if instance.woo_version == 'old':
                        response_url = product_categ and product_categ.get('image','')
                    elif instance.woo_version == 'new':
                        response_url = product_categ and product_categ.get('image') and product_categ.get('image',{}).get('src','') or ''
                    response_data.update({'response_url':response_url})                 
                if product_categ_id:
                    response_data.update({'woo_categ_id':product_categ_id,'slug':slug,'exported_in_woo':True})
                    woo_product_categ.write(response_data)
        return True
    
    @api.multi
    def update_product_categs_in_woo(self,instance,woo_product_categs):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()
        updated_categs=[]
        for woo_categ in woo_product_categs:
            if woo_categ in updated_categs :
                continue
            product_categs=[]
            product_categs.append(woo_categ)
            for categ in product_categs:
                if categ.parent_id and categ.parent_id not in product_categs and categ.parent_id not in updated_categs:
                    self.sync_product_category(instance, woo_product_categ=categ.parent_id)
                    product_categs.append(categ.parent_id)
                    
            product_categs.reverse()
            for woo_categ in product_categs:                
                img_url = ''
                if instance.is_image_url:                
                    if woo_categ.response_url:
                        try:
                            img = requests.get(woo_categ.response_url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:
                                img_url = woo_categ.response_url
                            elif woo_categ.url:
                                img_url = woo_categ.url
                        except Exception:
                            img_url = woo_categ.url or ''
                    elif woo_categ.url:
                        img_url = woo_categ.url
                else:
                    res = {}            
                    if woo_categ.image:
                        res = img_file_upload.upload_image(instance,woo_categ.image,"%s_%s"%(woo_categ.name,woo_categ.id))
                    img_url = res and res.get('url',False) or ''
                                                                
                row_data = {'name':str(woo_categ.name),
                            'display':str(woo_categ.display),                            
                            'description':str(woo_categ.description or '')}
                if woo_categ.slug:
                    row_data.update({'slug':str(woo_categ.slug)})
                img_url and row_data.update({'image' :img_url})
                if instance.woo_version == 'new' and img_url:
                    row_data.update({'image' :{'src':img_url}})
                woo_categ.parent_id.woo_categ_id and row_data.update({'parent':woo_categ.parent_id.woo_categ_id})
                if instance.woo_version == 'old':
                    data = {"product_category":row_data}
                    res =wcapi.put('products/categories/%s'%(woo_categ.woo_categ_id),data)
                elif instance.woo_version == 'new':
                    row_data.update({'id':woo_categ.woo_categ_id})
                    res =wcapi.post('products/categories/batch',{'update':[row_data]})
                if not isinstance(res,requests.models.Response):
                    transaction_log_obj.create({'message':"Update Product Category \nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'category',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if res.status_code not in [200,201]:
                    transaction_log_obj.create(
                                                    {'message':res.content,
                                                     'mismatch_details':True,
                                                     'type':'category',
                                                     'woo_instance_id':instance.id
                                                    })
                    continue                                    
                try:
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update product category with id %s to WooCommerce for instance %s. \n%s "%(woo_categ.woo_categ_id,instance.name,e),
                         'mismatch_details':True,
                         'type':'category',
                         'woo_instance_id':instance.id
                        })
                    continue
                if not isinstance(response,dict):
                    transaction_log_obj.create({'message':"Update Product Category \nResponse is not in proper format :: %s"%(response),
                                                 'mismatch_details':True,
                                                 'type':'category',
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
                                                     'type':'category',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue                
                    else:
                        if instance.is_image_url:
                            updated_product_category = response.get('product_category')
                            res_image = updated_product_category.get('image')
                            slug = updated_product_category.get('slug')             
                            res_image and woo_categ.write({'response_url':res_image,'slug':slug})                        
                elif instance.woo_version == 'new':                    
                    if instance.is_image_url:
                        updated_product_category = response
                        res_image = updated_product_category.get('image') and updated_product_category.get('image').get('src','')
                        slug = updated_product_category.get('slug')
                        res_image and woo_categ.write({'response_url':res_image,'slug':slug}) 
                updated_categs.append(woo_categ)
        return True
    
    def import_all_categories(self,wcapi,instance,transaction_log_obj,page):
        if instance.woo_version == 'old':
            res = wcapi.get("products/categories?filter[limit]=1000&page=%s"%(page))
        else:
            res = wcapi.get("products/categories?per_page=100&page=%s"%(page))
        if not isinstance(res,requests.models.Response):            
            transaction_log_obj.create({'message':"Get All Product Category \nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
            return []
        if res.status_code  not in [200,201]:
            transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'category',
                                     'woo_instance_id':instance.id
                                    })
            return []
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import product categories from WooCommerce for instance %s. \n%s"%(instance.name,e),
                 'mismatch_details':True,
                 'type':'category',
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
                                             'type':'category',
                                             'woo_instance_id':instance.id
                                            })
                return []
            return response.get('product_categories')
        elif instance.woo_version == 'new':            
            return response
    
    @api.multi
    def create_or_update_woo_categ(self,wcapi,instance,woo_product_categ_name,sync_images_with_product=True):
        transaction_log_obj = self.env['woo.transaction.log']
        woo_categ = False
        categ_name_list=[]
        product_categ_ids=[]
        wcapi = instance.connect_in_woo()
        categ_res=wcapi.get("products/categories?fields=id,name,parent")
        if not isinstance(categ_res,requests.models.Response):                               
            transaction_log_obj.create({'message':"Get Product Category \nResponse is not in proper format :: %s"%(categ_res),
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
            return False
        if categ_res.status_code  not in [200,201]:
            transaction_log_obj.create(
                                    {'message':categ_res.content,
                                     'mismatch_details':True,
                                     'type':'category',
                                     'woo_instance_id':instance.id
                                    })
            return False
        try:
            categ_response = categ_res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import product category %s from WooCommerce for instance %s. \n%s"%(woo_product_categ_name,instance.name,e),
                 'mismatch_details':True,
                 'type':'category',
                 'woo_instance_id':instance.id
                })
            return False
        if instance.woo_version == 'old':
            product_categories = categ_response.get('product_categories')
        elif instance.woo_version == 'new':
            product_categories = categ_response
        categ=list(filter(lambda categ: categ['name'].lower() == woo_product_categ_name.lower(), product_categories))
        if categ:
            categ=categ[0]
            product_categ_ids.append(categ.get('id'))
            categ_name_list.append(woo_product_categ_name.lower())
        for product_categ_id in product_categ_ids:
            tmp_categ=list(filter(lambda categ1: categ1['id'] == product_categ_id, product_categories))
            if tmp_categ:
                tmp_categ=tmp_categ[0]
                if tmp_categ.get('parent') and tmp_categ.get('parent') not in product_categ_ids:
                    product_categ_ids.append(tmp_categ.get('parent'))
                    tmp_parent_categ=list(filter(lambda categ2: categ2['id'] == tmp_categ.get('parent'), product_categories))
                    tmp_parent_categ and categ_name_list.append(tmp_parent_categ[0].get('name').lower())
                    
        product_categ_ids.reverse()
        for product_categ_id in product_categ_ids:
            response=wcapi.get("products/categories/%s"%(product_categ_id))            
            if not isinstance(response,requests.models.Response):
                transaction_log_obj.create({'message':"Get Product Category \nResponse is not in proper format :: %s"%(response),
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
                continue
            if response.status_code  not in [200,201]:
                transaction_log_obj.create(
                                        {'message':response.content,
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
                continue
            try:
                response = response.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While import product category with id %s from WooCommerce for instance %s. \n%s"%(product_categ_id,instance.name,e),
                     'mismatch_details':True,
                     'type':'category',
                     'woo_instance_id':instance.id
                    })
                continue
            if instance.woo_version == 'old':
                categ=response.get('product_category')
            elif instance.woo_version == 'new':
                categ=response
            product_category={'id':categ.get('id'),'name':categ.get('name')}
            categ_name = product_category.get('name')
            if categ_name.lower() in categ_name_list:                
                single_catg_res = wcapi.get("products/categories/%s"%(product_category.get('id')))
                if not isinstance(single_catg_res,requests.models.Response):                    
                    transaction_log_obj.create({'message':"Get Product Category \nResponse is not in proper format :: %s"%(single_catg_res),
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                try:
                    single_catg_response = single_catg_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import product category with id %s from WooCommerce for instance %s. \n%s"%(product_category.get('id'),instance.name,e),
                         'mismatch_details':True,
                         'type':'category',
                         'woo_instance_id':instance.id
                        })
                    continue
                if instance.woo_version == 'old':
                    single_catg = single_catg_response.get('product_category')
                elif instance.woo_version == 'new':
                    single_catg = single_catg_response
                parent_woo_id = single_catg.get('parent')
                parent_id=False
                binary_img_data = False
                if parent_woo_id:
                    parent_id=self.search([('woo_categ_id','=',parent_woo_id),('woo_instance_id','=',instance.id)],limit=1).id
                vals= {'name':categ_name,'woo_instance_id':instance.id,'parent_id':parent_id,'woo_categ_id':product_category.get('id'),'display':single_catg.get('display'),'slug':single_catg.get('slug'),'exported_in_woo':True,'description':single_catg.get('description','')}
                if sync_images_with_product:
                    res_image=False
                    if instance.woo_version == 'old':
                        res_image = single_catg.get('image')
                    elif instance.woo_version == 'new':                    
                        res_image = single_catg.get('image') and single_catg.get('image').get('src','')
                    if instance.is_image_url:                                    
                        res_image and vals.update({'response_url':res_image})
                    else:
                        if res_image:
                            try:
                                res_img = requests.get(res_image,stream=True,verify=False,timeout=10)
                                if res_img.status_code == 200:
                                    binary_img_data = base64.b64encode(res_img.content)                                                                                       
                            except Exception:
                                pass
                        binary_img_data and vals.update({'image':binary_img_data})
                woo_categ = self.search([('woo_categ_id','=',product_category.get('id')),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_categ:
                    woo_categ = self.search([('slug','=',product_category.get('slug')),('woo_instance_id','=',instance.id)],limit=1)
                if woo_categ:                                        
                    woo_categ.write(vals)                    
                else:                    
                    woo_categ = self.create(vals)                
        return woo_categ
    
    @api.multi
    def sync_product_category(self,instance,woo_product_categ=False,woo_product_categ_name=False,sync_images_with_product=True):
        transaction_log_obj=self.env["woo.transaction.log"]
        wcapi = instance.connect_in_woo()
        if woo_product_categ and woo_product_categ.exported_in_woo:
            response = wcapi.get("products/categories/%s"%(woo_product_categ.woo_categ_id))
            if not isinstance(response,requests.models.Response):                
                if not isinstance(response,requests.models.Response):                    
                    transaction_log_obj.create({'message':"Get Product Category \nResponse is not in proper format :: %s"%(response),
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
                return True
            if response.status_code == 404:
                self.export_product_categs(instance, [woo_product_categ])
                return True
        elif woo_product_categ and not woo_product_categ.exported_in_woo:
            woo_categ= self.create_or_update_woo_categ(wcapi,instance,woo_product_categ.name,sync_images_with_product)
            if woo_categ:
                return woo_categ
            else:
                self.export_product_categs(instance, [woo_product_categ])
                return True
        elif not woo_product_categ and woo_product_categ_name:
            woo_categ= self.create_or_update_woo_categ(wcapi,instance,woo_product_categ_name,sync_images_with_product)
            return woo_categ                                  
        else:
            if instance.woo_version == 'old':
                response = wcapi.get("products/categories?filter[limit]=1000")
            else:
                response = wcapi.get("products/categories?per_page=100")
            if not isinstance(response,requests.models.Response):                                
                transaction_log_obj.create({'message':"Get Product Category \nResponse is not in proper format :: %s"%(response),
                                     'mismatch_details':True,
                                     'type':'category',
                                     'woo_instance_id':instance.id
                                    })
                return True
            if response.status_code not in [200,201]:                    
                message = response.content           
                transaction_log_obj.create(
                                        {'message':message,
                                         'mismatch_details':True,
                                         'type':'category',
                                         'woo_instance_id':instance.id
                                        })
                return True
                        
        total_pages = 1
        if instance.woo_version == 'old':
            total_pages = response and response.headers.get('X-WC-TotalPages') or 1
        elif instance.woo_version == 'new':                    
            total_pages = response and response.headers.get('x-wp-totalpages') or 1
        try:
            res = response.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import product categories from WooCommerce for instance %s. \n%s"%(instance.name,e),
                 'mismatch_details':True,
                 'type':'category',
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
                                             'type':'category',
                                             'woo_instance_id':instance.id
                                            })
                return True            
            if woo_product_categ:
                response =  res.get('product_category')
                results = [response]
            else:
                results = res.get('product_categories')
        elif instance.woo_version == 'new':                        
            if woo_product_categ:                
                results = [res]
            else:
                results = res
        if int(total_pages) >=2:
            for page in range(2,int(total_pages)+1):            
                results = results + self.import_all_categories(wcapi,instance,transaction_log_obj,page)

        processed_categs=[]
        for res in results:
            if not isinstance(res, dict):
                continue 
            if res.get('id',False) in processed_categs:
                continue
            
            categ_results=[]
            categ_results.append(res)
            for categ_result in categ_results:
                if not isinstance(categ_result, dict):
                    continue
                if categ_result.get('parent'):
                    parent_categ=list(filter(lambda categ: categ['id'] == categ_result.get('parent'), results))
                    if parent_categ:
                        parent_categ=parent_categ[0]
                    else:
                        response=wcapi.get("products/categories/%s"%(categ_result.get('parent')))
                        if not isinstance(response,requests.models.Response):                            
                            transaction_log_obj.create({'message':"Get Product Category \nResponse is not in proper format :: %s"%(response),
                                     'mismatch_details':True,
                                     'type':'category',
                                     'woo_instance_id':instance.id
                                    })
                            continue
                        try:
                            response = response.json()
                        except Exception as e:
                            transaction_log_obj.create({'message':"Json Error : While import parent category for category %s from WooCommerce for instance %s. \n%s"%(categ_result.get('name'),instance.name,e),
                                 'mismatch_details':True,
                                 'type':'category',
                                 'woo_instance_id':instance.id
                                })
                            continue
                        if instance.woo_version == 'old':
                            parent_categ=response.get('product_category')
                        elif instance.woo_version == 'new':
                            parent_categ=response
                    if parent_categ not in categ_results:
                        categ_results.append(parent_categ)
                    
            categ_results.reverse()
            for result in categ_results:
                if not isinstance(result, dict):
                    continue
                if result.get('id') in processed_categs:
                    continue
                
                woo_categ_id = result.get('id')
                woo_categ_name = result.get('name')
                display = result.get('display')
                slug = result.get('slug')
                parent_woo_id=result.get('parent')
                parent_id=False
                binary_img_data = False
                if parent_woo_id:
                    parent_id=self.search([('woo_categ_id','=',parent_woo_id),('woo_instance_id','=',instance.id)],limit=1).id
                vals= {'name':woo_categ_name,'woo_instance_id':instance.id,'display':display,'slug':slug,'exported_in_woo':True,'parent_id':parent_id,'description':result.get('description','')}
                if sync_images_with_product:
                    res_image = False
                    if instance.woo_version == 'old':
                        res_image = result.get('image')
                    elif instance.woo_version == 'new':                    
                        res_image = result.get('image') and result.get('image').get('src','')
                                    
                    if instance.is_image_url:                                    
                        res_image and vals.update({'response_url':res_image})
                    else:
                        if res_image:
                            try:
                                res_img = requests.get(res_image,stream=True,verify=False,timeout=10)
                                if res_img.status_code == 200:
                                    binary_img_data = base64.b64encode(res_img.content)                                                                                       
                            except Exception:
                                pass
                        binary_img_data and vals.update({'image':binary_img_data})
                vals.update({'woo_categ_id':woo_categ_id,'slug':slug})                                                   
                woo_product_categ = self.search([('woo_categ_id','=',woo_categ_id),('woo_instance_id','=',instance.id)])
                if not woo_product_categ:
                    woo_product_categ = self.search([('slug','=',slug),('woo_instance_id','=',instance.id)],limit=1)                    
                if woo_product_categ:                                                                                                                        
                    woo_product_categ.write(vals)
                else:                    
                    self.create(vals)
                    
                processed_categs.append(result.get('id',False))
        return True