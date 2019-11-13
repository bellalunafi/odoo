from odoo import models,fields,api
import odoo.addons.decimal_precision as dp
from datetime import datetime
from .. img_upload import img_file_upload
import base64
import requests
import hashlib
from odoo.tools.misc import flatten

class woo_product_template_ept(models.Model):
    _name="woo.product.template.ept"
    _order='product_tmpl_id'
    _description = "WooCommerce Product Template"
    
    @api.multi
    @api.depends('woo_product_ids.exported_in_woo','woo_product_ids.variant_id')
    def get_total_sync_variants(self):
        woo_product_obj=self.env['woo.product.product.ept']
        for template in self:
            variants=woo_product_obj.search([('id','in',template.woo_product_ids.ids),('exported_in_woo','=',True),('variant_id','!=',False)]) 
            template.total_sync_variants=len(variants.ids)
           
    name=fields.Char("Name",translate=True)
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",required=1)
    product_tmpl_id=fields.Many2one("product.template","Product Template",required=1)
    woo_categ_ids = fields.Many2many('woo.product.categ.ept','woo_template_categ_rel','woo_template_id','woo_categ_id',"Categories")
    woo_tag_ids = fields.Many2many('woo.tags.ept','woo_template_tags_rel','woo_template_id','woo_tag_id',"Tags")
    woo_tmpl_id=fields.Char("Woo Template Id")
    exported_in_woo=fields.Boolean("Exported In Woo")
    woo_product_ids=fields.One2many("woo.product.product.ept","woo_template_id","Products")
    woo_gallery_image_ids=fields.One2many("woo.product.image.ept","woo_product_tmpl_id","Images")    
    created_at=fields.Datetime("Created At")
    updated_at=fields.Datetime("Updated At")           
    taxable=fields.Boolean("Taxable",default=True)    
    website_published=fields.Boolean('Available in the website', copy=False)    
    description=fields.Html("Description",translate=True)
    short_description=fields.Html("Short Description",translate=True)
    total_variants_in_woo=fields.Integer("Total Varaints in Woo",default=0,help="Total Variants in WooCommerce,\nDisplay after sync products")
    total_sync_variants=fields.Integer("Total Sync Variants",compute="get_total_sync_variants",store=True)
       
    @api.onchange("product_tmpl_id")
    def on_change_product(self):
        for record in self:
            record.name=record.product_tmpl_id.name            

    @api.multi
    def woo_unpublished(self):
        instance=self.woo_instance_id
        wcapi = instance.connect_in_woo()
        transaction_log_obj=self.env['woo.transaction.log']
        if self.woo_tmpl_id:
            info = {'status':'draft'}
            data = info
            if instance.woo_version == 'old':
                data = {'product':info}                       
                res = wcapi.put('products/%s'%(self.woo_tmpl_id),data)
            else:
                data.update({'id':self.woo_tmpl_id})
                res = wcapi.post('products/batch',{'update':[data]})
            if not isinstance(res,requests.models.Response):               
                transaction_log_obj.create({'message': "Unpublish Product \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                return True
            if res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                return True
            try:            
                response = res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While Unpublish Product with id %s from WooCommerce for instance %s. \n%s"%(self.woo_tmpl_id,instance.name,e),
                             'mismatch_details':True,
                             'type':'product',
                             'woo_instance_id':instance.id
                            })
                return False
            if instance.woo_version == 'old':            
                errors = response.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':"Can not Unpublish Template,  %s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                else:                    
                    self.write({'website_published':False})
            elif instance.woo_version == 'new':
                if response.get('data',{}) and response.get('data',{}).get('status') not in [200,201]:
                    message = response.get('message')
                    transaction_log_obj.create(
                                                {'message':"Can not Unpublish Template,  %s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                else:                                            
                    self.write({'website_published':False})
        return True           

    @api.multi
    def woo_published(self):
        instance=self.woo_instance_id
        wcapi = instance.connect_in_woo()
        transaction_log_obj=self.env['woo.transaction.log']
        if self.woo_tmpl_id:
            info = {'status':'publish'}
            data = info
            if instance.woo_version == 'old':
                data = {'product':info}
                res = wcapi.put('products/%s'%(self.woo_tmpl_id),data)
            else:
                data.update({'id':self.woo_tmpl_id})
                res = wcapi.post('products/batch',{'update':[data]})
            if not isinstance(res,requests.models.Response):                
                transaction_log_obj.create({'message': "Publish Product \nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                return True
            if res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                return True            
            try:            
                response = res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While Publish Product with id %s from WooCommerce for instance %s. \n%s"%(self.woo_tmpl_id,instance.name,e),
                             'mismatch_details':True,
                             'type':'product',
                             'woo_instance_id':instance.id
                            })
                return False
            if instance.woo_version == 'old':            
                errors = response.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':"Can not Publish Template,  %s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                else:                    
                    self.write({'website_published':True})
                    
            elif instance.woo_version == 'new':
                if response.get('data',{}) and response.get('data',{}).get('status') not in [200,201]:
                    message = response.get('message')
                    transaction_log_obj.create(
                                                {'message':"Can not Publish Template,  %s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                else:                    
                    self.write({'website_published':True})
        return True
    
    @api.multi
    def sync_new_woo_categ_with_product(self,wcapi,instance,woo_categories,sync_images_with_product=True):
        obj_woo_product_categ=self.env['woo.product.categ.ept']
        categ_ids = []
        for woo_category in woo_categories:
            woo_product_categ = obj_woo_product_categ.search([('woo_categ_id','=',woo_category.get('id')),('woo_instance_id','=',instance.id)],limit=1)
            if not woo_product_categ:
                woo_product_categ = obj_woo_product_categ.search([('slug','=',woo_category.get('slug')),('woo_instance_id','=',instance.id)],limit=1)
            if woo_product_categ:
                woo_product_categ.write({'woo_categ_id':woo_category.get('id'),'name':woo_category.get('name'),'display':woo_category.get('display'),'slug':woo_category.get('slug'),'exported_in_woo':True})
                obj_woo_product_categ.sync_product_category(instance,woo_product_categ=woo_product_categ,sync_images_with_product=sync_images_with_product)
                categ_ids.append(woo_product_categ.id)                                                   
            else:
                woo_product_categ = obj_woo_product_categ.create({'woo_categ_id':woo_category.get('id'),'name':woo_category.get('name'),'display':woo_category.get('display'),'slug':woo_category.get('slug'),'woo_instance_id':instance.id,'exported_in_woo':True})
                obj_woo_product_categ.sync_product_category(instance,woo_product_categ=woo_product_categ,sync_images_with_product=sync_images_with_product)
                woo_product_categ and categ_ids.append(woo_product_categ.id)                        
        return categ_ids
    
    @api.multi
    def sync_new_woo_tags_with_product(self,wcapi,instance,woo_tags):
        obj_woo_product_tags=self.env['woo.tags.ept']        
        tag_ids = []
        for woo_tag in woo_tags:
            woo_product_tag = obj_woo_product_tags.search([('woo_tag_id','=',woo_tag.get('id')),('woo_instance_id','=',instance.id)],limit=1)
            if not woo_product_tag:
                woo_product_tag = obj_woo_product_tags.search([('slug','=',woo_tag.get('slug')),('woo_instance_id','=',instance.id)],limit=1)
            if woo_product_tag:
                woo_product_tag.write({'name':woo_tag.get('name'),'slug':woo_tag.get('slug'),'exported_in_woo':True})
                obj_woo_product_tags.sync_product_tags(instance,woo_product_tag=woo_product_tag)
                tag_ids.append(woo_product_tag.id)
            else:
                woo_product_tag = obj_woo_product_tags.create({'woo_tag_id':woo_tag.get('id'),'name':woo_tag.get('name'),'slug':woo_tag.get('slug'),'woo_instance_id':instance.id,'exported_in_woo':True})
                obj_woo_product_tags.sync_product_tags(instance,woo_product_tag=woo_product_tag)
                woo_product_tag and tag_ids.append(woo_product_tag.id)
        return tag_ids    
    
    @api.multi
    def sync_woo_categ_with_product(self,wcapi,instance,woo_categories,sync_images_with_product=True):
        woo_product_categ=self.env['woo.product.categ.ept']
        categ_ids = []
        for woo_category in woo_categories:
            ctg = woo_category.lower().replace('\'','\'\'')
            self._cr.execute("select id from woo_product_categ_ept where LOWER(name) = '%s' and woo_instance_id = %s limit 1"%(ctg,instance.id))
            woo_product_categ_id = self._cr.dictfetchall()
            woo_categ=False
            if woo_product_categ_id:
                woo_categ = woo_product_categ.browse(woo_product_categ_id[0].get('id'))                
                categ_ids.append(woo_categ.id)                
                woo_categ = woo_product_categ.sync_product_category(instance,woo_product_categ=woo_categ,sync_images_with_product=sync_images_with_product)                    
            else:
                woo_categ = woo_product_categ.sync_product_category(instance,woo_product_categ_name=woo_category,sync_images_with_product=sync_images_with_product)
                woo_categ and categ_ids.append(woo_categ.id)                        
        return categ_ids
    
    @api.multi
    def sync_woo_tags_with_product(self,wcapi,instance,woo_tags):
        transaction_log_obj=self.env['woo.transaction.log']
        woo_product_tags=self.env['woo.tags.ept']        
        tag_ids = []
        for woo_tag in woo_tags:
            tag = woo_tag.lower().replace('\'','\'\'')
            self._cr.execute("select id from woo_tags_ept where LOWER(name) = '%s' and woo_instance_id = %s limit 1"%(tag,instance.id))
            woo_product_tag_id = self._cr.dictfetchall()
            woo_product_tag=False
            if woo_product_tag_id:
                woo_product_tag = woo_product_tags.browse(woo_product_tag_id[0].get('id'))
                tag_ids.append(woo_product_tag.id)                                                  
            else:
                tag_res=wcapi.get("products/tags?fields=id,name")
                if not isinstance(tag_res,requests.models.Response):                    
                    transaction_log_obj.create({'message': "Get Product Tags\nResponse is not in proper format :: %s"%(tag_res),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                    continue
                if tag_res.status_code not in [200,201]:
                    transaction_log_obj.create(
                                        {'message':tag_res.content,
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                    continue                
                try:            
                    tag_response = tag_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While Sync Product Tags from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                product_tags = tag_response.get('product_tags')
                if isinstance(product_tags,dict):
                    product_tags = [product_tags]
                for product_tag in product_tags:
                    tag_name = product_tag.get('name')
                    if tag_name == woo_tag:
                        single_tag_res = wcapi.get("products/tags/%s"%(product_tag.get('id')))
                        if not isinstance(single_tag_res,requests.models.Response):                            
                            transaction_log_obj.create({'message': "Get Product Tags\nResponse is not in proper format :: %s"%(single_tag_res),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                            continue
                        try:            
                            single_tag_response = single_tag_res.json()
                        except Exception as e:
                            transaction_log_obj.create({'message':"Json Error : While Sync Product Tag with id %s from WooCommerce for instance %s. \n%s"%(woo_tag.woo_tag_id,instance.name,e),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                            continue
                        single_tag = single_tag_response.get('product_tag')
                        
                        tag_vals = {'name':woo_tag,'woo_instance_id':instance.id,'description':single_tag.get('description'),'exported_in_woo':True,'woo_tag_id':single_tag.get('id')}
                            
                        woo_product_tag = woo_product_tags.create(tag_vals)
                        woo_product_tag and tag_ids.append(woo_product_tag.id)
                        break        
        return tag_ids    

    def import_all_attribute_terms(self,wcapi,instance,woo_attribute_id,transaction_log_obj,page):
        if instance.woo_version=='new':
            res = wcapi.get("products/attributes/%s/terms?per_page=100&page=%s"%(woo_attribute_id.woo_attribute_id,page))
        else:
            res = wcapi.get("products/attributes/%s/terms?filter[limit]=1000&page=%s"%(woo_attribute_id.woo_attribute_id,page))
        if not isinstance(res,requests.models.Response):            
            transaction_log_obj.create({'message':"Get All Attibute Terms \nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            return []
        if res.status_code  not in [200,201]:
            transaction_log_obj.create(
                                    {'message':res.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
            return []
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import product attribute terms from WooCommerce for instance %s. \n%s "%(instance.name,e),
                 'mismatch_details':True,
                 'type':'product',
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
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                return []
            return response.get('product_attribute_terms')
        elif instance.woo_version == 'new':            
            return response
    
    @api.multi
    def sync_woo_attribute_term(self,instance):
        transaction_log_obj=self.env['woo.transaction.log']
        obj_woo_attribute=self.env['woo.product.attribute.ept']
        obj_woo_attribute_term=self.env['woo.product.attribute.term.ept']
        odoo_attribute_value_obj=self.env['product.attribute.value']
        
        wcapi = instance.connect_in_woo()
        woo_attributes = obj_woo_attribute.search([])
        attributes_term_data=[]
        for woo_attribute in woo_attributes:
            if instance.woo_version=='new':
                response = wcapi.get("products/attributes/%s/terms?per_page=100"%(woo_attribute.woo_attribute_id))
            else:
                response = wcapi.get("products/attributes/%s/terms?filter[limit]=1000"%(woo_attribute.woo_attribute_id))
            try:
                attributes_term_data = response.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While import product attribute terms from WooCommerce for instance %s. \n%s "%(instance.name,e),
                     'mismatch_details':True,
                     'type':'product',
                     'woo_instance_id':instance.id
                    })
                return False
            if instance.woo_version=='old':
                attributes_term_data = attributes_term_data.get('product_attribute_terms')
            if not isinstance(attributes_term_data, list):
                transaction_log_obj.create({'message':"Response is not in proper format :: %s"%(attributes_term_data),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            total_pages = 1
            if instance.woo_version == 'old':
                total_pages = response and response.headers.get('X-WC-TotalPages') or 1
            elif instance.woo_version == 'new':                    
                total_pages = response and response.headers.get('x-wp-totalpages') or 1
            if int(total_pages) >=2:
                for page in range(2,int(total_pages)+1):            
                    attributes_term_data = attributes_term_data + self.import_all_attribute_terms(wcapi,instance,woo_attribute,transaction_log_obj,page)
            if response.status_code in [201,200]:
                for attribute_term in attributes_term_data:
                    woo_attribute_term = obj_woo_attribute_term.search([('woo_attribute_term_id','=',attribute_term.get('id')),('woo_instance_id','=',instance.id),('exported_in_woo','=',True)],limit=1)
                    if woo_attribute_term:
                        continue
                    odoo_attribute_value=odoo_attribute_value_obj.search([('name','=ilike',attribute_term.get('name')),('attribute_id','=',woo_attribute.attribute_id.id)],limit=1)
                    if not odoo_attribute_value:
                        odoo_attribute_value=odoo_attribute_value.with_context(active_id=False).create({'name':attribute_term.get('name'),'attribute_id':woo_attribute.attribute_id.id})
                    woo_attribute_term = obj_woo_attribute_term.search([('attribute_value_id','=',odoo_attribute_value.id),('attribute_id','=',woo_attribute.attribute_id.id),('woo_attribute_id','=',woo_attribute.id),('woo_instance_id','=',instance.id),('exported_in_woo','=',False)],limit=1)
                    if woo_attribute_term:
                        woo_attribute_term.write({'woo_attribute_term_id':attribute_term.get('id'),'count':attribute_term.get('count'),'slug':attribute_term.get('slug'),'exported_in_woo':True})
                    else:
                        obj_woo_attribute_term.create({'name':attribute_term.get('name'),'woo_attribute_term_id':attribute_term.get('id'),
                                  'slug':attribute_term.get('slug'),'woo_instance_id':instance.id,'attribute_value_id':odoo_attribute_value.id,
                                  'woo_attribute_id':woo_attribute.woo_attribute_id,'attribute_id':woo_attribute.attribute_id.id,
                                  'exported_in_woo':True,'count':attribute_term.get('count')})
            else:
                transaction_log_obj.create(
                                        {'message':attribute_term.content,
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                continue
        return True
    
    def import_all_attributes(self,wcapi,instance,transaction_log_obj,page):
        if instance.woo_version=='new':
            res=wcapi.get('products/attributes?per_page=100&page=%s'%(page))
        else:
            res=wcapi.get('products/attributes?filter[limit]=1000&page=%s'%(page))
        if not isinstance(res,requests.models.Response):            
            transaction_log_obj.create({'message':"Get All Attibutes \nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'product',
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
            transaction_log_obj.create({'message':"Json Error : While import product attributes from WooCommerce for instance %s. \n%s "%(instance.name,e),
                 'mismatch_details':True,
                 'type':'product',
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
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                return []
            return response.get('product_attributes')
        elif instance.woo_version == 'new':            
            return response
    
    @api.multi
    def sync_woo_attribute(self,instance):
        transaction_log_obj=self.env['woo.transaction.log']
        obj_woo_attribute=self.env['woo.product.attribute.ept']
        odoo_attribute_obj=self.env['product.attribute']
        
        wcapi = instance.connect_in_woo()
        if instance.woo_version=='new':
            response = wcapi.get("products/attributes?per_page=100")
        else:
            response = wcapi.get('products/attributes?filter[limit]=1000')
        try:
            attributes_data = response.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While import product attributes from WooCommerce for instance %s. \n%s "%(instance.name,e),
                 'mismatch_details':True,
                 'type':'product',
                 'woo_instance_id':instance.id
                })
            return False
        if instance.woo_version=='old':
            attributes_data = response.get('product_attributes')
        total_pages = 1
        if instance.woo_version == 'old':
            total_pages = response and response.headers.get('X-WC-TotalPages') or 1
        elif instance.woo_version == 'new':                    
            total_pages = response and response.headers.get('x-wp-totalpages') or 1
        if not isinstance(attributes_data, list):
            transaction_log_obj.create({'message':"Response is not in proper format :: %s"%(attributes_data),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            return True
        if int(total_pages) >=2:
            for page in range(2,int(total_pages)+1):            
                attributes_data = attributes_data + self.import_all_attributes(wcapi,instance,transaction_log_obj,page)
        if response.status_code in [201,200]:
            for attribute in attributes_data:
                woo_attribute = obj_woo_attribute.search([('woo_attribute_id','=',attribute.get('id')),('woo_instance_id','=',instance.id),('exported_in_woo','=',True)],limit=1)
                if woo_attribute:
                    continue
                odoo_attribute=odoo_attribute_obj.search([('name','=ilike',attribute.get('name'))],limit=1)
                if not odoo_attribute:
                    odoo_attribute=odoo_attribute.create({'name':attribute.get('name')})
                woo_attribute = obj_woo_attribute.search([('attribute_id','=',odoo_attribute.id),('woo_instance_id','=',instance.id),('exported_in_woo','=',False)],limit=1)
                if woo_attribute:
                    woo_attribute.write({'woo_attribute_id':attribute.get('id'),'order_by':attribute.get('order_by'),'slug':attribute.get('slug'),'exported_in_woo':True,'has_archives':attribute.get('has_archives')})
                else:
                    obj_woo_attribute.create({'name':attribute.get('name'),'woo_attribute_id':attribute.get('id'),'order_by':attribute.get('order_by'),
                              'slug':attribute.get('slug'),'woo_instance_id':instance.id,'attribute_id':odoo_attribute.id,
                              'exported_in_woo':True,'has_archives':attribute.get('has_archives')})
        else:
            transaction_log_obj.create(
                                    {'message':attributes_data.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
            return True
        self.sync_woo_attribute_term(instance)
        return True
    
    @api.multi
    def export_product_attributes_in_woo(self,instance,attribute):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()
        obj_woo_attribute=self.env['woo.product.attribute.ept']
        woo_attribute = obj_woo_attribute.search([('attribute_id','=',attribute.id),('woo_instance_id','=',instance.id),('exported_in_woo','=',True)],limit=1)
        if woo_attribute and woo_attribute.woo_attribute_id:
            return {attribute.id:woo_attribute.woo_attribute_id}                                     
        attribute_data = {'name':attribute.name,                                  
                          'type':'select',                              
                         }        
        if instance.woo_version=='old':
            attribute_data={'product_attribute':attribute_data}
        attribute_res = wcapi.post("products/attributes", attribute_data)
        if not isinstance(attribute_res,requests.models.Response):
            transaction_log_obj.create({'message':"Export Product Attributes \nResponse is not in proper format :: %s"%(attribute_res),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            return False                                   
        if attribute_res.status_code == 400:
            self.sync_woo_attribute(instance)
            woo_attribute = obj_woo_attribute.search([('attribute_id','=',attribute.id),('woo_instance_id','=',instance.id),('exported_in_woo','=',True)],limit=1)
            if woo_attribute and woo_attribute.woo_attribute_id:
                return {attribute.id:woo_attribute.woo_attribute_id}
        if attribute_res.status_code not in [200,201]:
            transaction_log_obj.create(
                                {'message':attribute_res.content,
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
            return False
        attribute_response = attribute_res.json()
        if instance.woo_version=='old':
            attribute_response=attribute_response.get('product_attribute')
        woo_attribute_id = attribute_response.get('id')
        woo_attribute_name = attribute_response.get('name')
        woo_attribute_slug = attribute_response.get('slug')
        woo_attribute_order_by = attribute_response.get('order_by')
        has_archives = attribute_response.get('has_archives')
        obj_woo_attribute.create({'name':attribute and attribute.name or woo_attribute_name,'woo_attribute_id':woo_attribute_id,'order_by':woo_attribute_order_by,
                                  'slug':woo_attribute_slug,'woo_instance_id':instance.id,'attribute_id':attribute.id,
                                  'exported_in_woo':True,'has_archives':has_archives})
        return {attribute.id:woo_attribute_id}

    def import_all_draft_products(self,wcapi,instance,transaction_log_obj,page):
        res=wcapi.get('products?filter[post_status]=draft&page=%s'%(page))
        if not isinstance(res,requests.models.Response):            
            transaction_log_obj.create({'message': "Get All Draft Products\nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
            return []
        if res.status_code not in [200,201]:
            transaction_log_obj.create(
                                {'message':res.content,
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })            
            return []
        try:            
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While Import Draft Products from WooCommerce for instance %s. \n%s"%(instance.name,e),
                         'mismatch_details':True,
                         'type':'product',
                         'woo_instance_id':instance.id
                        })
            return []
        return response.get('products')    
    
    def import_all_products(self,wcapi,instance,transaction_log_obj,page):
        if instance.woo_version == 'new':
            res=wcapi.get('products?per_page=100&page=%s'%(page))
        else:            
            res=wcapi.get('products?page=%s'%(page))
        if not isinstance(res,requests.models.Response):            
            transaction_log_obj.create({'message': "Get All Products\nResponse is not in proper format :: %s"%(res),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
            return []
        if res.status_code not in [200,201]:
            transaction_log_obj.create(
                                {'message':res.content,
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })            
            return []
        try:            
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While Import Product from WooCommerce for instance %s. \n%s"%(instance.name,e),
                         'mismatch_details':True,
                         'type':'product',
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
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                return []
            return response.get('products')
        elif instance.woo_version == 'new':            
            return response
    
    @api.multi
    def set_variant_sku(self,instance,result,product_template,sync_price_with_product=False):
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        odoo_product_obj=self.env['product.product']
        woo_attribute_obj=self.env['woo.product.attribute.ept']
        woo_attribute_term_obj=self.env['woo.product.attribute.term.ept']

        for variation in result.get('variations'):                
            sku = variation.get('sku')
            price = variation.get('regular_price') or variation.get('sale_price')
            attribute_value_ids = []
            domain = []
            odoo_product = False
            variation_attributes = variation.get('attributes')
            
            for variation_attribute in variation_attributes:
                attribute_val = variation_attribute.get('option')
                attribute_name = variation_attribute.get('name')
                if instance.attribute_type=='text':
                    for attribute in result.get('attributes'):
                        if attribute.get('variation') and attribute.get('name'):
                            if attribute.get('name').replace(" ", "-").lower() == attribute_name:
                                attribute_name = attribute.get('name')
                                break
                    product_attribute = product_attribute_obj.search([('name','=ilike',attribute_name)],limit=1)
                    if product_attribute:
                        product_attribute_value = product_attribute_value_obj.search([('attribute_id','=',product_attribute.id),('name','=ilike',attribute_val)],limit=1)
                        product_attribute_value and attribute_value_ids.append(product_attribute_value.id)
                if instance.attribute_type=='select':
                    woo_product_attribute = woo_attribute_obj.search([('name','=ilike',attribute_name)],limit=1)
                    if woo_product_attribute:
                        woo_product_attribute_term = woo_attribute_term_obj.search([('woo_attribute_id','=',woo_product_attribute.woo_attribute_id),('name','=ilike',attribute_val)],limit=1)
                        if not woo_product_attribute_term:
                            woo_product_attribute_term = woo_attribute_term_obj.search([('woo_attribute_id','=',woo_product_attribute.woo_attribute_id),('slug','=ilike',attribute_val)],limit=1)
                        woo_product_attribute_term and attribute_value_ids.append(woo_product_attribute_term.attribute_value_id.id)

            for attribute_value_id in attribute_value_ids:
                tpl = ('attribute_value_ids','=',attribute_value_id)
                domain.append(tpl)
            domain and domain.append(('product_tmpl_id','=',product_template.id))
            if domain:    
                odoo_product = odoo_product_obj.search(domain) 
            odoo_product and odoo_product.write({'default_code':sku})
            if odoo_product and sync_price_with_product:
                pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',odoo_product.id)],limit=1)
                if not pricelist_item:
                    instance.pricelist_id.write({
                        'item_ids': [(0,0,{
                            'applied_on': '0_product_variant',
                            'product_id':odoo_product.id ,
                            'compute_price': 'fixed',
                            'fixed_price': price})]
                        })
                else:
                    pricelist_item.write({'fixed_price':price})
                odoo_product.write({'list_price':price})
        return True
    
    @api.multi
    def create_variant_product(self,result,instance):
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        product_template_obj = self.env['product.template']
        
        template_title = ''
        if result.get('name',''):
            template_title = result.get('name')
        if result.get('title',''):
            template_title = result.get('title')
        attrib_line_vals = []
                        
        for attrib in result.get('attributes'):
            if not attrib.get('variation'):
                continue
            attrib_name = attrib.get('name')    
            attrib_values = attrib.get('options')
            attribute=product_attribute_obj.get_attribute(attrib_name,type='radio',create_variant='always',auto_create=True)
            attr_val_ids = []
            
            for attrib_vals in attrib_values:
                attrib_value = product_attribute_value_obj.get_attribute_values(attrib_vals,attribute.id,auto_create=True)
                attr_val_ids.append(attrib_value.id)
            
            if attr_val_ids:
                attribute_line_ids_data = [0, False,{'attribute_id': attribute.id,'value_ids':[[6, False, attr_val_ids]]}]
                attrib_line_vals.append(attribute_line_ids_data)
        if attrib_line_vals:
            product_template = product_template_obj.create({'name':template_title,
                                        'type':'product',
                                        'attribute_line_ids':attrib_line_vals,
                                        'description_sale':result.get('description','')})   
            self.set_variant_sku(instance,result,product_template,sync_price_with_product=instance.sync_price_with_product)
        else:
            return False
        return True
    
    @api.multi
    def set_variant_images(self,odoo_product_images):
        for odoo_product_image in odoo_product_images:
            binary_img_data = odoo_product_image.get('image',False)
            odoo_product = odoo_product_image.get('odoo_product',False)
            if odoo_product:
                odoo_product.write({'image':binary_img_data})
    
    @api.multi
    def is_product_importable(self,result,instance,odoo_product,woo_product):
        woo_skus = []
        odoo_skus = []
        variations = result.get('variations')
        
        if instance.woo_version == "new":
            template_title = result.get('name')
        else:
            template_title = result.get('title')
            
        product_count = len(variations)
        
        importable = True
        message = ""
        
        if not odoo_product and not woo_product:
            if product_count != 0:
                attributes=1
                for attribute in result.get('attributes'):
                    if attribute.get('variation'):
                        attributes*=len(attribute.get('options'))
                
            product_attributes={}
            for variantion in variations:
                sku = variantion.get("sku")
                attributes=variantion.get('attributes')
                attributes and product_attributes.update({sku:attributes})
                sku and woo_skus.append(sku)
            if not product_attributes and result.get('type')=='variable':
                message="Attributes are not set in any variation of Product: %s and ID: %s."%(template_title,result.get("id"))                          
                importable = False
                return importable,message
            if woo_skus:
                woo_skus = list(filter(lambda x: len(x)>0, woo_skus))
            total_woo_sku = len(set(woo_skus))
            if not len(woo_skus) == total_woo_sku:
                message="Duplicate SKU found in Product: %s and ID: %s."%(template_title,result.get("id"))                          
                importable = False
                return importable,message
        woo_skus=[]    
        if odoo_product:
            odoo_template = odoo_product.product_tmpl_id
            if not (product_count == 0 and odoo_template.product_variant_count == 1):
                if product_count == odoo_template.product_variant_count:
                    for woo_sku,odoo_sku in zip(result.get('variations'),odoo_template.product_variant_ids):
                        woo_skus.append(woo_sku.get('sku'))
                        odoo_sku.default_code and odoo_skus.append(odoo_sku.default_code)
                    
                    woo_skus = list(filter(lambda x: len(x)>0, woo_skus))
                    odoo_skus = list(filter(lambda x: len(x)>0, odoo_skus)) 
                    
                    total_woo_sku = len(set(woo_skus))
                    if not len(woo_skus) == total_woo_sku:
                        message="Duplicate SKU found in Product: %s and ID: %s."%(template_title,result.get("id"))                          
                        importable = False
                        return importable,message
                    
        if woo_product:
            woo_skus = []
            for woo_sku in result.get('variations'):
                woo_skus.append(woo_sku.get('sku'))

            total_woo_sku = len(set(woo_skus))
            if not len(woo_skus) == total_woo_sku:
                message="Duplicate SKU found in Product: %s and ID: %s."%(template_title,result.get("id"))                          
                importable = False
                return importable,message
        
        return importable,message
    
    @api.multi
    def sync_gallery_images(self,instance,result,woo_template,odoo_product_images,woo_product_img):
        images = result.get('images')
        existing_gallery_img_keys = {}
        if not instance.is_image_url:                
            for gallery_img in woo_template.woo_gallery_image_ids:
                if not gallery_img.image:
                    continue
                key=hashlib.md5(gallery_img.image).hexdigest()
                if not key:
                    continue
                existing_gallery_img_keys.update({key:gallery_img})            
        for image in images:
            if str(image.get('name').encode('utf-8')) == 'Placeholder' or not image.get('id'):
                continue                
            image_id = image.get('id')
            res_image_src = image.get('src')
            position = image.get('position')
            binary_img_data = False
            if not instance.is_image_url and res_image_src:                    
                try:
                    res_img = requests.get(res_image_src,stream=True,verify=False,timeout=10)
                    if res_img.status_code == 200:
                        binary_img_data = base64.b64encode(res_img.content)
                        key=hashlib.md5(binary_img_data).hexdigest()
                        if key in existing_gallery_img_keys:
                            gallery_image = existing_gallery_img_keys.get(key)
                            gallery_image.write({'sequence':position,'woo_image_id':image_id})
                            continue
                        if position == 0:
                            if not instance.is_image_url and not result.get('variations'):                
                                woo_template.woo_product_ids[0].product_id.image = binary_img_data
                            if not instance.is_image_url and result.get('variations'):
                                woo_template.product_tmpl_id.write({'image': binary_img_data})
                                odoo_product_images and self.set_variant_images(odoo_product_images)
                except Exception:
                    pass                    
            
            if res_image_src:
                if position == 0:
                    if not instance.is_image_url and not result.get('variations'):                
                        woo_template.woo_product_ids[0].product_id.image = binary_img_data
                    if not instance.is_image_url and result.get('variations'):
                        woo_template.product_tmpl_id.write({'image': binary_img_data})
                        odoo_product_images and self.set_variant_images(odoo_product_images)
                woo_product_tmp_img = woo_product_img.search([('woo_product_tmpl_id','=',woo_template.id),('woo_instance_id','=',instance.id),('woo_image_id','=',image_id)],limit=1)
                if woo_product_tmp_img:
                    if instance.is_image_url:
                        woo_product_tmp_img.write({'response_url':res_image_src,'sequence':position})
                    else:
                        woo_product_tmp_img.write({'image':binary_img_data,'sequence':position})
                else:                                                                      
                    if instance.is_image_url:
                        woo_product_img.create({'woo_instance_id':instance.id,'sequence':position,'woo_product_tmpl_id':woo_template.id,'response_url':res_image_src,'woo_image_id':image_id})
                    else:
                        woo_product_img.create({'woo_instance_id':instance.id,'sequence':position,'woo_product_tmpl_id':woo_template.id,'image':binary_img_data,'woo_image_id':image_id})
    
    @api.multi
    def get_product_response(self,instance,woo_tmpl_id,wcapi,transaction_log_obj):
        results=[]
        if woo_tmpl_id:
            res=wcapi.get('products/%s'%(woo_tmpl_id))            
        else:
            res=wcapi.get('products?per_page=100')                               
        if not isinstance(res,requests.models.Response):                                                         
            transaction_log_obj.create({'message': "Get Products\nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            return False
        if res.status_code not in [200,201]:
            transaction_log_obj.create(
                                {'message':res.content,
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
            return False
        total_pages = res.headers.get('x-wp-totalpages',0)         
        try:            
            res = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While Import Product from WooCommerce for instance %s. \n%s"%(instance.name,e),
                         'mismatch_details':True,
                         'type':'product',
                         'woo_instance_id':instance.id
                        })
            return []
        if woo_tmpl_id:            
            results = [res]
        else:
            results = res
        if int(total_pages) >=2:
            for page in range(2,int(total_pages)+1):            
                results = results + self.import_all_products(wcapi,instance,transaction_log_obj,page)
        if instance.is_latest:
            for result in results:
                variants=[]
                woo_id=result.get('id')
                for variant in result.get('variations'):
                    try:            
                        variants.append(wcapi.get('products/%s/variations/%s'%(woo_id,variant)).json())
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While Import Product Variants from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                result.update({'variations':variants})
        return results
        
    @api.model    
    def create_woo_product(self,woo_product_obj,vals,result,instance):
        woo_prodcut = woo_product_obj.create(vals)
        return woo_prodcut
    
    @api.model
    def update_woo_product(self,vals,woo_product,result,instance):
        woo_product = woo_product.write(vals)
        return woo_product
    
    @api.model
    def create_woo_template(self,vals,result,instance):
        woo_template=self.create(vals)
        return woo_template
    
    @api.model
    def update_woo_template(self,vals,woo_template,result,instance):
        woo_template = woo_template.write(vals)
        return woo_template

    @api.multi
    def sync_products(self,instance,woo_tmpl_id=False,update_price=False,update_templates=True,sync_images_with_product=False, skip_existing_products=False):
        if instance.attribute_type=='select':
            self.sync_woo_attribute(instance)
        woo_product_obj=self.env['woo.product.product.ept']
        transaction_log_obj=self.env["woo.transaction.log"]
        woo_product_img = self.env['woo.product.image.ept']    
        product_template_obj = self.env['product.template']    
        odoo_product_obj=self.env['product.product']                       
        wcapi = instance.connect_in_woo()
        
        categ_ids = []
        tag_ids = []
        is_importable = True
        message = ""
                
        if woo_tmpl_id:
            res=wcapi.get('products/%s'%(woo_tmpl_id))
        else:
            res=wcapi.get('products?filter[limit]=6000')            
            
        if not isinstance(res,requests.models.Response):                                 
            transaction_log_obj.create({'message': "Get Products\nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            return False
        if res.status_code not in [200,201]:
            transaction_log_obj.create(
                                {'message':res.content,
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
            return False                                    
        total_pages = res.headers.get('X-WC-TotalPages')        
        try:            
            res = res.json()
        except Exception as e:
            transaction_log_obj.create({'message':"Json Error : While Sync Products from WooCommerce for instance %s. \n%s"%(instance.name,e),
                         'mismatch_details':True,
                         'type':'product',
                         'woo_instance_id':instance.id
                        })
            return False        
        if not isinstance(res, dict):
            transaction_log_obj.create(
                                        {'message':"Sync Products, Response is not in proper format",
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            return True
                    
        errors = res.get('errors','')
        if errors:
            message = errors[0].get('message')
            transaction_log_obj.create(
                                        {'message':message,
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            return True
        
        if woo_tmpl_id:
            response = res.get('product')
            results = [response]
        else:
            results = res.get('products')
            draft_res=wcapi.get('products?filter[post_status]=draft&filter[limit]=6000')
            if not isinstance(draft_res,requests.models.Response):                                 
                transaction_log_obj.create({'message': "Get Draft Products\nResponse is not in proper format :: %s"%(draft_res),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })            
            if draft_res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':draft_res.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })                                                
            draft_total_pages = draft_res.headers.get('X-WC-TotalPages')        
            try:            
                draft_res = draft_res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While Sync Draft Products from WooCommerce for instance %s. \n%s"%(instance.name,e),
                             'mismatch_details':True,
                             'type':'product',
                             'woo_instance_id':instance.id
                            })
                draft_res = []
            if not isinstance(draft_res, dict):
                transaction_log_obj.create(
                                            {'message':"Sync Draft Products,Response is not in proper format",
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
            results = results + draft_res.get('products')
            if draft_total_pages and int(draft_total_pages) >=2:
                for page in range(2,int(draft_total_pages)+1):            
                    results = results + self.import_all_draft_products(wcapi,instance,transaction_log_obj,page)
        if int(total_pages) >=2:
            for page in range(2,int(total_pages)+1):            
                results = results + self.import_all_products(wcapi,instance,transaction_log_obj,page)
                
        for result in results:
            woo_product=False
            odoo_product=False
                                        
            woo_tmpl_id = result.get('id')
            template_title = result.get('title')
            template_created_at = result.get('created_at')
            template_updated_at = result.get('updated_at')
            
            if template_created_at.startswith('-'):
                template_created_at = template_created_at[1:]                 
            if template_updated_at.startswith('-'):
                template_updated_at = template_updated_at[1:]
            
            short_description = result.get('short_description')
            description = result.get('description')
            status = result.get('status')
            taxable = result.get('taxable')            

            website_published = False
            if status == 'publish':
                website_published = True
                            
            tmpl_info = {'name':template_title,'created_at':template_created_at,'updated_at':template_updated_at,
                         'short_description':short_description,'description':description,
                         'website_published':website_published,'taxable':taxable}            
            
            woo_template = self.search([('woo_tmpl_id','=',woo_tmpl_id),('woo_instance_id','=',instance.id)],limit=1)
            if woo_template and not update_templates:
                continue
            updated_template=False                        
            onetime_call=False
            for variation in result.get('variations'):                
                variant_id = variation.get('id')
                sku = variation.get('sku')                                               
                                
                woo_product = woo_product_obj.search([('variant_id','=',variant_id),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('product_id.default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)                                    
                if not woo_product:
                    odoo_product=odoo_product_obj.search([('default_code','=',sku)],limit=1)
                if woo_product and skip_existing_products:
                    # Added code for skip the product sync if already product imported
                    continue
                is_importable = True
                message = ""
                
                is_importable,message = self.is_product_importable(result,instance,odoo_product,woo_product)
                if not is_importable:
                    if not transaction_log_obj.search([("message","=",message)],limit=1):                   
                        transaction_log_obj.create(                                              
                                            {'message':message,                                              
                                             'mismatch_details':True,                                     
                                             'type':'product',                                  
                                             'woo_instance_id':instance.id})
                    break
                
                if not odoo_product and not woo_product:
                    if instance.auto_import_product:                       
                        if not onetime_call:
                            self.create_variant_product(result,instance)
                            odoo_product = odoo_product_obj.search([('default_code','=',sku)],limit=1)
                            onetime_call = True
                            if not odoo_product:
                                message="Attribute(s) are not set properly in Product: %s and ID: %s."%(template_title,result.get('id'))
                                if not transaction_log_obj.search([("message","=",message)],limit=1):                       
                                    transaction_log_obj.create(                                              
                                                {'message':message,                                              
                                                 'mismatch_details':True,                                     
                                                 'type':'product',                                  
                                                'woo_instance_id':instance.id})
                                break
                    else:
                        message="%s Product Not found for sku %s"%(template_title,sku)
                        if not transaction_log_obj.search([("message","=",message)],limit=1):                          
                            transaction_log_obj.create(                                              
                                                {'message':message,                                              
                                                 'mismatch_details':True,                                     
                                                 'type':'product',                                  
                                                'woo_instance_id':instance.id})
                        continue
                
                variant_info = {}                               
                var_img = False
                price = variation.get('regular_price') or variation.get('sale_price')
                if sync_images_with_product:
                    var_images =  variation.get('image')
                    var_image_src = ''
                    var_image_id = False                
                    for var_image in var_images:
                        if str(var_image.get('title').encode('utf-8')) == 'Placeholder' or not var_image.get('id'):
                            continue
                        if var_image.get('position') == 0:                        
                            var_image_src = var_image.get('src')
                            var_image_id = var_image.get('id')
                            if not instance.is_image_url and var_image_src:
                                try:
                                    res_img = requests.get(var_image_src,stream=True,verify=False,timeout=10)
                                    if res_img.status_code == 200:
                                        var_img = base64.b64encode(res_img.content)                                                                                       
                                except Exception:
                                    pass                        
                            
                created_at = variation.get('created_at')
                updated_at = variation.get('updated_at')
                if created_at.startswith('-'):
                    created_at = created_at[1:]                 
                if updated_at.startswith('-'):
                    updated_at = updated_at[1:]
                    
                variant_info = {'name':template_title,'default_code':sku,'created_at':created_at,'updated_at':updated_at}
                if instance.is_image_url and sync_images_with_product:
                    variant_info.update({'response_url':var_image_src,'woo_image_id':var_image_id})
                                                                                       
                if not woo_product:                                       
                    if not woo_template:
                        woo_categories=result.get('categories')
                        categ_ids = self.sync_woo_categ_with_product(wcapi,instance,woo_categories,sync_images_with_product)
                                                    
                        woo_tags=result.get('tags')
                        tag_ids = self.sync_woo_tags_with_product(wcapi,instance,woo_tags)                                                                                                                    
                        tmpl_info.update({'product_tmpl_id':odoo_product.product_tmpl_id.id,'woo_instance_id':instance.id,
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,                                     
                                     'exported_in_woo':True,'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],
                                     'total_variants_in_woo':len(result.get('variations'))                                     
                                     })
                        
                        woo_template=self.create(tmpl_info)                                                                
                    variant_info.update({'product_id':odoo_product.id,
                             'name':template_title,
                             'variant_id':variant_id,
                             'woo_template_id':woo_template.id,                                 
                             'woo_instance_id':instance.id,                                                                 
                             'exported_in_woo':True,    
                             })               
                    woo_product = woo_product_obj.create(variant_info)
                    if not instance.is_image_url:
                        odoo_product.image = var_img if woo_product else None
                    if update_price:
                        woo_product.product_id.write({'list_price':price.replace(",",".")})
                else:
                    if not updated_template:
                        woo_categories=result.get('categories')
                        categ_ids = self.sync_woo_categ_with_product(wcapi,instance,woo_categories,sync_images_with_product)
                                                    
                        woo_tags=result.get('tags')
                        tag_ids = self.sync_woo_tags_with_product(wcapi,instance,woo_tags)                        
                        tmpl_info.update({
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,                                     
                                     'exported_in_woo':True,
                                     'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],
                                     'total_variants_in_woo':len(result.get('variations'))                                     
                                     })                                                                                                                                                                                                                               
                        updated_template=True                        
                        if not woo_template:
                            woo_template=woo_product.woo_template_id                            

                        woo_template.write(tmpl_info)                                            
                    variant_info.update({                             
                             'variant_id':variant_id,
                             'woo_template_id':woo_template.id,                                 
                             'woo_instance_id':instance.id,                                                                 
                             'exported_in_woo':True,                                 
                             })     
                    if update_price:
                        pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',odoo_product.id)],limit=1)
                        if not pricelist_item:
                            instance.pricelist_id.write({
                                'item_ids': [(0,0,{
                                    'applied_on': '0_product_variant',
                                    'product_id':odoo_product.id ,
                                    'compute_price': 'fixed',
                                    'fixed_price': price})]
                                })
                        else:
                            pricelist_item.write({'fixed_price':price})
                    woo_product.write(variant_info)
                    if not instance.is_image_url and sync_images_with_product:
                        woo_product.product_id.image = var_img if woo_product else None                        
            if not result.get('variations'):
                sku=result.get('sku')
                price = result.get('regular_price') or result.get('sale_price')
                woo_product = woo_product_obj.search([('variant_id','=',woo_tmpl_id),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('product_id.default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)                        
                if not woo_product:
                    odoo_product=odoo_product_obj.search([('default_code','=',sku)],limit=1)                    
                
                is_importable = True
                is_importable,message = self.is_product_importable(result,instance,odoo_product,woo_product)
                if not is_importable:
                    if not transaction_log_obj.search([("message","=",message)],limit=1):                   
                        transaction_log_obj.create(                                              
                                            {'message':message,                                              
                                             'mismatch_details':True,                                     
                                             'type':'product',                                  
                                             'woo_instance_id':instance.id})
                    continue
                               
                if not odoo_product and not woo_product:
                    if sku:
                        if not result.get('parent_id'):
                            if instance.auto_import_product == True:
                                vals={'name':template_title,
                                                        'default_code':sku,
                                                        'type':'product',
                                                        }
                                product_template = product_template_obj.create(vals)
                                odoo_product = product_template.product_variant_ids
                                if instance.sync_price_with_product:
                                    pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',odoo_product.id)],limit=1)
                                    if not pricelist_item:
                                        instance.pricelist_id.write({
                                            'item_ids': [(0,0,{
                                                'applied_on': '0_product_variant',
                                                'product_id':odoo_product.id ,
                                                'compute_price': 'fixed',
                                                'fixed_price': price})]
                                            })
                                else:
                                    pricelist_item.write({'fixed_price':price})
                            else:
                                message="%s Product Not found for sku %s"%(template_title,sku)
                                if not transaction_log_obj.search([("message","=",message)],limit=1):                          
                                    transaction_log_obj.create(                                              
                                                        {'message':message,                                              
                                                         'mismatch_details':True,                                     
                                                         'type':'product',                                  
                                                        'woo_instance_id':instance.id})
                                continue
                        else:
                            message="%s Product and id %s and sku %s is a variant product it cannot import."%(template_title,result.get('id'),sku)
                            if not transaction_log_obj.search([("message","=",message)],limit=1):                          
                                transaction_log_obj.create(                                              
                                                    {'message':message,                                              
                                                     'mismatch_details':True,                                     
                                                     'type':'product',                                  
                                                    'woo_instance_id':instance.id})
                            continue
                    else:
                        message="SKU not set in Product: %s and ID: %s."%(template_title,result.get('id'))
                        if not transaction_log_obj.search([("message","=",message)],limit=1):                          
                            transaction_log_obj.create(                                              
                                                {'message':message,                                              
                                                 'mismatch_details':True,                                     
                                                 'type':'product',                                  
                                                'woo_instance_id':instance.id})
                        continue
                        
                woo_categories=result.get('categories')
                categ_ids = self.sync_woo_categ_with_product(wcapi,instance,woo_categories,sync_images_with_product)
                                            
                woo_tags=result.get('tags')
                tag_ids = self.sync_woo_tags_with_product(wcapi,instance,woo_tags)
                if not woo_product:                                       
                    if not woo_template:                                                                                      
                        tmpl_info.update({'product_tmpl_id':odoo_product.product_tmpl_id.id,'woo_instance_id':instance.id,
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,
                                     'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],                                     
                                     'exported_in_woo':True,
                                     'total_variants_in_woo':1                                     
                                     })
                        
                        woo_template=self.create(tmpl_info)                        
                    variant_info = {'name':template_title,'default_code':sku,'created_at':template_created_at,
                                    'updated_at':template_updated_at,'product_id':odoo_product.id,                             
                                    'variant_id':woo_tmpl_id,'woo_template_id':woo_template.id,                                 
                                    'woo_instance_id':instance.id,'exported_in_woo':True}               
                    woo_product = woo_product_obj.create(variant_info)                    
                    if update_price:
                        pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',odoo_product.id)],limit=1)
                        if not pricelist_item:
                            instance.pricelist_id.write({
                                'item_ids': [(0,0,{
                                    'applied_on': '0_product_variant',
                                    'product_id':odoo_product.id,
                                    'compute_price': 'fixed',
                                    'fixed_price': price})]
                                })
                        else:
                            pricelist_item.write({'fixed_price':price})
                else:
                    if not updated_template:                        
                        tmpl_info.update({
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,
                                     'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],                                     
                                     'exported_in_woo':True,
                                     'total_variants_in_woo':1                                     
                                     })                                                                                                                                                                                                                               
                        updated_template=True                        
                        if not woo_template:
                            woo_template=woo_product.woo_template_id                            

                        woo_template.write(tmpl_info)                                            
                    variant_info = {'name':template_title,'default_code':sku,'created_at':template_created_at,'updated_at':template_updated_at,
                                    'variant_id':woo_tmpl_id,'woo_template_id':woo_template.id,'woo_instance_id':instance.id,                                                                 
                                    'exported_in_woo':True}     
                    woo_product.write(variant_info) 
                    if update_price:
                        pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',woo_product.product_id.id)],limit=1)
                        if not pricelist_item:
                            instance.pricelist_id.write({
                                'item_ids': [(0,0,{
                                    'applied_on': '0_product_variant',
                                    'product_id':woo_product.product_id.id ,
                                    'compute_price': 'fixed',
                                    'fixed_price': price})]
                                })
                        else:
                            pricelist_item.write({'fixed_price':price})                   
            if is_importable and woo_template and sync_images_with_product:
                variant_info = {}
                tmpl_info = {}
                                                                                                  
                images = result.get('images')
                
                existing_gallery_img_keys = {}
                if not instance.is_image_url:                
                    for gallery_img in woo_template.woo_gallery_image_ids:
                        if not gallery_img.image:
                            continue
                        key=hashlib.md5(gallery_img.image).hexdigest()
                        if not key:
                            continue
                        existing_gallery_img_keys.update({key:gallery_img})                        
                for image in images:                
                    if str(image.get('title').encode('utf-8')) == 'Placeholder' or not image.get('id'):
                        continue
                    image_id = image.get('id')
                    res_image_src = image.get('src')
                    position = image.get('position')
                    binary_img_data = False
                    if not instance.is_image_url and res_image_src:                    
                        try:
                            res_img = requests.get(res_image_src,stream=True,verify=False,timeout=10)
                            if res_img.status_code == 200:
                                binary_img_data = base64.b64encode(res_img.content)
                                key=hashlib.md5(binary_img_data).hexdigest()
                                if key in existing_gallery_img_keys:
                                    gallery_image = existing_gallery_img_keys.get(key)
                                    gallery_image.write({'sequence':position,'woo_image_id':image_id})
                                    continue
                                if position == 0:
                                    if not instance.is_image_url and not result.get('variations'):                
                                        woo_template.woo_product_ids[0].product_id.image = binary_img_data
                        except Exception:
                            pass                    
                    
                    if res_image_src:
                        if position == 0:
                            if not instance.is_image_url and not result.get('variations'):                
                                woo_template.woo_product_ids[0].product_id.image = binary_img_data
                        woo_product_tmp_img= woo_product_img.search([('woo_product_tmpl_id','=',woo_template.id),('woo_instance_id','=',instance.id),('woo_image_id','=',image_id)],limit=1)
                        if woo_product_tmp_img:
                            if instance.is_image_url:
                                woo_product_tmp_img.write({'response_url':res_image_src,'sequence':position})
                            else:
                                woo_product_tmp_img.write({'image':binary_img_data,'sequence':position})                        
                        else:                                                                      
                            if instance.is_image_url:
                                woo_product_img.create({'woo_instance_id':instance.id,'sequence':position,'woo_product_tmpl_id':woo_template.id,'response_url':res_image_src,'woo_image_id':image_id})
                            else:
                                woo_product_img.create({'woo_instance_id':instance.id,'sequence':position,'woo_product_tmpl_id':woo_template.id,'image':binary_img_data,'woo_image_id':image_id})
            self._cr.commit()
        return True
    
    @api.multi
    def sync_new_products(self,instance,woo_tmpl_id=False,update_price=False,update_templates=True,sync_images_with_product=False, skip_existing_products=False):
        if instance.attribute_type=='select' and not woo_tmpl_id:
            self.sync_woo_attribute(instance)
        woo_product_obj=self.env['woo.product.product.ept']
        transaction_log_obj=self.env["woo.transaction.log"]
        woo_product_img = self.env['woo.product.image.ept']  
        product_template_obj = self.env['product.template']      
        odoo_product_obj=self.env['product.product']                       
        wcapi = instance.connect_in_woo()
        
        categ_ids = []
        tag_ids = []
        odoo_product_images = []
        categ_and_tag_imported=True
        results = self.get_product_response(instance, woo_tmpl_id, wcapi, transaction_log_obj)
        if woo_tmpl_id:
            categ_and_tag_imported=False
        if categ_and_tag_imported:
            self.env['woo.product.categ.ept'].sync_product_category(instance,sync_images_with_product=sync_images_with_product)
            self.env['woo.tags.ept'].sync_product_tags(instance)
        if not results:
            return False
        for result in results:
            woo_product=False
            odoo_product=False
            product_url=result.get('permalink',False)                            
            woo_tmpl_id = result.get('id')
            template_title = result.get('name')
            template_created_at = result.get('date_created')
            template_updated_at = result.get('date_modified')
            
            if template_created_at and template_created_at.startswith('-'):
                template_created_at = template_created_at[1:]                 
            if template_updated_at and template_updated_at.startswith('-'):
                template_updated_at = template_updated_at[1:]
            
            short_description = result.get('short_description')
            description = result.get('description')
            status = result.get('status')
            tax_status = result.get('tax_status')
            
            taxable = True
            if tax_status != 'taxable':             
                taxable = False
            website_published = False
            if status == 'publish':
                website_published = True
                            
            tmpl_info = {'name':template_title,'created_at':template_created_at or False,
                         'updated_at':template_updated_at or False,
                         'short_description':short_description,'description':description,
                         'website_published':website_published,'taxable':taxable}            
            
            woo_template = self.search([('woo_tmpl_id','=',woo_tmpl_id),('woo_instance_id','=',instance.id)],limit=1)
            if woo_template and not update_templates:
                continue
            updated_template=False
            is_importable = False
            onetime_call = False      
            for variation in result.get('variations'):                
                variant_id = variation.get('id')
                sku = variation.get('sku')                                               
                product_url = variation.get('permalink',False)
                
                woo_product = woo_product_obj.search([('variant_id','=',variant_id),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('product_id.default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    odoo_product=odoo_product_obj.search([('default_code','=',sku)],limit=1)
                if woo_product:
                    odoo_product=woo_product.product_id
                    # Added code for skip the product sync if already product imported
                    if skip_existing_products:
                        continue
                is_importable = True
                message = ""
                
                is_importable,message = self.is_product_importable(result,instance,odoo_product,woo_product)
                if not is_importable:
                    if not transaction_log_obj.search([("message","=",message)],limit=1):                   
                        transaction_log_obj.create(                                              
                                            {'message':message,                                              
                                             'mismatch_details':True,                                     
                                             'type':'product',                                  
                                             'woo_instance_id':instance.id})
                    break
                
                if not odoo_product and not woo_product and not woo_template:
                    if instance.auto_import_product:
                        if not onetime_call:
                            self.create_variant_product(result,instance)
                            odoo_product = odoo_product_obj.search([('default_code','=',sku)],limit=1)
                            onetime_call = True
                    else:
                        message="%s Product Not found for sku %s"%(template_title,sku)
                        if not transaction_log_obj.search([("message","=",message)],limit=1):                          
                            transaction_log_obj.create(                                              
                                                {'message':message,                                              
                                                 'mismatch_details':True,                                     
                                                 'type':'product',                                  
                                                'woo_instance_id':instance.id})
                        continue
                
                if not odoo_product:
                    continue
                variant_info = {}                               
                var_img = False
                price = variation.get('regular_price') or variation.get('sale_price')
                if sync_images_with_product:
                    var_images =  variation.get('image')
                    if instance.is_latest:
                        var_images=[var_images]
                    var_image_src = ''
                    var_image_id = False                
                    for var_image in var_images:
                        if str(var_image.get('name').encode('utf-8')) == 'Placeholder' or not var_image.get('id'):
                            continue
                        if var_image.get('position') == 0:                        
                            var_image_src = var_image.get('src')
                            var_image_id = var_image.get('id')
                            if not instance.is_image_url and var_image_src:
                                try:
                                    res_img = requests.get(var_image_src,stream=True,verify=False,timeout=10)
                                    if res_img.status_code == 200:
                                        var_img = base64.b64encode(res_img.content)         
                                except Exception:
                                    pass                        
                            
                created_at = variation.get('date_created')
                updated_at = variation.get('date_modified')
                if created_at and created_at.startswith('-'):
                    created_at = created_at[1:]                 
                if updated_at and updated_at.startswith('-'):
                    updated_at = updated_at[1:]
                    
                variant_info = {'name':template_title,'default_code':sku,'created_at':created_at or False,'updated_at':updated_at or False,'producturl':product_url or False}
                if instance.is_image_url and sync_images_with_product:
                    variant_info.update({'response_url':var_image_src,'woo_image_id':var_image_id})
                                                                                       
                if not woo_product:                                       
                    if not woo_template:
                        woo_categories=result.get('categories')
                        if not categ_and_tag_imported:
                            categ_ids = self.sync_new_woo_categ_with_product(wcapi,instance,woo_categories,sync_images_with_product)
                        else:
                            woo_categs=[]
                            for woo_category in woo_categories:
                                woo_categ=woo_category.get('id') and self.env['woo.product.categ.ept'].search([('woo_categ_id','=',woo_category.get('id'))],limit=1)
                                woo_categ and woo_categs.append(woo_categ.id)
                            categ_ids=woo_categs and woo_categs or []
                        woo_tags=result.get('tags')
                        if not categ_and_tag_imported:
                            tag_ids = self.sync_new_woo_tags_with_product(wcapi,instance,woo_tags)
                        else:
                            product_tags=[]
                            for woo_tag in woo_tags:
                                product_tag=woo_tag.get('id') and self.env['woo.tags.ept'].search([('woo_tag_id','=',woo_tag.get('id'))],limit=1)
                                product_tag and product_tags.append(product_tag.id)
                            tag_ids=product_tags and product_tags or []
                        tmpl_info.update({'product_tmpl_id':odoo_product.product_tmpl_id.id,'woo_instance_id':instance.id,
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,                                     
                                     'exported_in_woo':True,'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],
                                     'total_variants_in_woo':len(result.get('variations'))                                     
                                     })
                        woo_template=self.create_woo_template(tmpl_info,result,instance)                                                                
                    
                    variant_info.update(
                        {'product_id':odoo_product.id,
                             'name':template_title,
                             'variant_id':variant_id,
                             'woo_template_id':woo_template.id,                                 
                             'woo_instance_id':instance.id,                                                                 
                             'exported_in_woo':True,
                             'producturl':product_url,                                 
                             })               
                    woo_product = self.create_woo_product(woo_product_obj, variant_info, result, instance)
                    if not instance.is_image_url and sync_images_with_product:
                        odoo_product_images.append({'odoo_product':odoo_product,'image':var_img if woo_product else None,'sku':sku})
                    if update_price:
                        pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',odoo_product.id)],limit=1)
                        if not pricelist_item:
                            instance.pricelist_id.write({
                                'item_ids': [(0,0,{
                                    'applied_on': '0_product_variant',
                                    'product_id':odoo_product.id ,
                                    'compute_price': 'fixed',
                                    'fixed_price': price})]
                                })
                        else:
                            pricelist_item.write({'fixed_price':price})
                else:
                    if not updated_template:
                        woo_categories=result.get('categories')
                        if not categ_and_tag_imported:
                            categ_ids = self.sync_new_woo_categ_with_product(wcapi,instance,woo_categories,sync_images_with_product)
                        else:
                            woo_categs=[]
                            for woo_category in woo_categories:
                                woo_categ=woo_category.get('id') and self.env['woo.product.categ.ept'].search([('woo_categ_id','=',woo_category.get('id'))],limit=1)
                                woo_categ and woo_categs.append(woo_categ.id)
                            categ_ids=woo_categs and woo_categs or []
                                                    
                        woo_tags=result.get('tags')
                        if not categ_and_tag_imported:
                            tag_ids = self.sync_new_woo_tags_with_product(wcapi,instance,woo_tags)
                        else:
                            product_tags=[]
                            for woo_tag in woo_tags:
                                product_tag=woo_tag.get('id') and self.env['woo.tags.ept'].search([('woo_tag_id','=',woo_tag.get('id'))],limit=1)
                                product_tag and product_tags.append(product_tag.id)
                            tag_ids=product_tags and product_tags or []                        
                        tmpl_info.update({
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,                                     
                                     'exported_in_woo':True,
                                     'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],
                                     'total_variants_in_woo':len(result.get('variations'))                                     
                                     })                                                                                                                                                                                                                               
                        updated_template=True                        
                        if not woo_template:
                            woo_template=woo_product.woo_template_id                            
                        self.update_woo_template(tmpl_info, woo_template, result, instance)                                            
                    variant_info.update({                             
                             'variant_id':variant_id,
                             'woo_template_id':woo_template.id,                                 
                             'woo_instance_id':instance.id,                                                                 
                             'exported_in_woo':True,                                 
                             })     
                    self.update_woo_product(variant_info, woo_product, result, instance)
                    if update_price:
                        pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',woo_product.product_id.id)],limit=1)
                        if not pricelist_item:
                            instance.pricelist_id.write({
                                'item_ids': [(0,0,{
                                    'applied_on': '0_product_variant',
                                    'product_id':woo_product.product_id.id ,
                                    'compute_price': 'fixed',
                                    'fixed_price': price})]
                                })
                        else:
                            pricelist_item.write({'fixed_price':price})
                    if not instance.is_image_url and sync_images_with_product:
                        odoo_product_images.append({'odoo_product':odoo_product,'image':var_img if woo_product else None,'sku':sku})
                        if var_img:
                            odoo_product.image=var_img
            
            if not result.get('variations'):
                is_importable=True
                sku=result.get('sku')
                product_url=result.get('permalink',False)
                price = result.get('regular_price') or result.get('sale_price')
                woo_product = woo_product_obj.search([('variant_id','=',woo_tmpl_id),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product:
                    woo_product=woo_product_obj.search([('product_id.default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)                        
                if not woo_product:
                    odoo_product=odoo_product_obj.search([('default_code','=',sku)],limit=1)
                
                is_importable = True
                is_importable,message = self.is_product_importable(result,instance,odoo_product,woo_product)
                if not is_importable:
                    if not transaction_log_obj.search([("message","=",message)],limit=1):                   
                        transaction_log_obj.create(                                              
                                            {'message':message,                                              
                                             'mismatch_details':True,                                     
                                             'type':'product',                                  
                                             'woo_instance_id':instance.id})
                    continue
                                    
                if not odoo_product and not woo_product:
                    if sku:
                        if instance.auto_import_product == True:
                            if instance.auto_import_product == True:
                                vals={'name':template_title,
                                        'default_code':sku,
                                        'type':'product',
                                        'producturl':product_url,
                                        }
                                product_template = product_template_obj.create(vals)
                                odoo_product = product_template.product_variant_ids
                                if instance.sync_price_with_product:
                                    pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',odoo_product.id)],limit=1)
                                    if not pricelist_item:
                                        instance.pricelist_id.write({
                                            'item_ids': [(0,0,{
                                                'applied_on': '0_product_variant',
                                                'product_id':odoo_product.id ,
                                                'compute_price': 'fixed',
                                                'fixed_price': price})]
                                            })
                                    else:
                                        pricelist_item and pricelist_item.write({'fixed_price':price})
                                    odoo_product.write({'list_price':price})
                        else:
                            message="%s Product  Not found for sku %s"%(template_title,sku)
                            if not transaction_log_obj.search([("message","=",message)],limit=1):                          
                                transaction_log_obj.create(                                              
                                                    {'message':message,                                              
                                                     'mismatch_details':True,                                     
                                                     'type':'product',                                  
                                                    'woo_instance_id':instance.id})
                            continue
                    else:
                        message="SKU not set in Product: %s and ID: %s."%(template_title,result.get('id'))
                        if not transaction_log_obj.search([("message","=",message)],limit=1):                          
                            transaction_log_obj.create({'message':message,                                              
                                                 'mismatch_details':True,                                     
                                                 'type':'product',                                  
                                                'woo_instance_id':instance.id})
                        continue
                woo_categories=result.get('categories')
                if not categ_and_tag_imported:
                    categ_ids = self.sync_new_woo_categ_with_product(wcapi,instance,woo_categories,sync_images_with_product)
                else:
                    woo_categs=[]
                    for woo_category in woo_categories:
                        woo_categ=woo_category.get('id') and self.env['woo.product.categ.ept'].search([('woo_categ_id','=',woo_category.get('id'))],limit=1)
                        woo_categ and woo_categs.append(woo_categ.id)
                    categ_ids=woo_categs and woo_categs or []
                                            
                woo_tags=result.get('tags')
                if not categ_and_tag_imported:
                    tag_ids = self.sync_new_woo_tags_with_product(wcapi,instance,woo_tags)
                else:
                    product_tags=[]
                    for woo_tag in woo_tags:
                        product_tag=woo_tag.get('id') and self.env['woo.tags.ept'].search([('woo_tag_id','=',woo_tag.get('id'))],limit=1)
                        product_tag and product_tags.append(product_tag.id)
                    tag_ids=product_tags and product_tags or []
                if not woo_product:                                       
                    if not woo_template:                                                                                      
                        tmpl_info.update({'product_tmpl_id':odoo_product.product_tmpl_id.id,'woo_instance_id':instance.id,
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,
                                     'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],                                     
                                     'exported_in_woo':True,
                                     'total_variants_in_woo':1                                     
                                     })
                        woo_template=self.create_woo_template(tmpl_info,result,instance)
                    variant_info = {'name':template_title,'default_code':sku,'created_at':template_created_at,
                                    'updated_at':template_updated_at,'product_id':odoo_product.id,                             
                                    'variant_id':woo_tmpl_id,'woo_template_id':woo_template.id,                                 
                                    'woo_instance_id':instance.id,'exported_in_woo':True,'producturl':product_url}               
                    woo_product = woo_product_obj.create(variant_info)                    
                    if update_price:
                        pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',odoo_product.id)],limit=1)
                        if not pricelist_item:
                            instance.pricelist_id.write({
                                'item_ids': [(0,0,{
                                    'applied_on': '0_product_variant',
                                    'product_id':odoo_product.id ,
                                    'compute_price': 'fixed',
                                    'fixed_price': price})]
                                })
                        else:
                            pricelist_item.write({'fixed_price':price})
                else:
                    if not updated_template:                        
                        tmpl_info.update({
                                     'woo_tmpl_id':woo_tmpl_id,'taxable':taxable,
                                     'woo_categ_ids':[(6, 0, categ_ids)],
                                     'woo_tag_ids':[(6, 0, tag_ids)],                                     
                                     'exported_in_woo':True,
                                     'total_variants_in_woo':1                                     
                                     })                                                                                                                                                                                                                               
                        updated_template=True                        
                        if not woo_template:
                            woo_template=woo_product.woo_template_id                            
                        self.update_woo_template(tmpl_info, woo_template, result, instance)
                    variant_info = {'name':template_title,'default_code':sku,'created_at':template_created_at,'updated_at':template_updated_at,
                                    'variant_id':woo_tmpl_id,'woo_template_id':woo_template.id,'woo_instance_id':instance.id,                                                                 
                                    'exported_in_woo':True}     
                    self.update_woo_product(variant_info, woo_product, result, instance)
                    if update_price:
                        pricelist_item=self.env['product.pricelist.item'].search([('pricelist_id','=',instance.pricelist_id.id),('product_id','=',woo_product.product_id.id)],limit=1)
                        if not pricelist_item:
                            instance.pricelist_id.write({
                                'item_ids': [(0,0,{
                                    'applied_on': '0_product_variant',
                                    'product_id':woo_product.product_id.id ,
                                    'compute_price': 'fixed',
                                    'fixed_price': price})]
                                })
                        else:
                            pricelist_item.write({'fixed_price':price})
            if is_importable and woo_template and sync_images_with_product:
                self.sync_gallery_images(instance, result, woo_template, odoo_product_images, woo_product_img)
            self._cr.commit()
        return True
                
    @api.model
    def set_old_products_images_in_woo(self,instance):
        transaction_log_obj=self.env['woo.transaction.log']
        woo_product_img = self.env['woo.product.image.ept']             
        wcapi = instance.connect_in_woo()
        flag = False
        for template in self:
            odoo_template = template.product_tmpl_id                                         
            data = {}                    
            tmpl_images=[]                           
            position = 0
            gallery_img_keys={}
            key = False    
            for br_gallery_image in template.woo_gallery_image_ids:                               
                img_url = ''
                if instance.is_image_url:
                    if br_gallery_image.response_url:
                        try:
                            img = requests.get(br_gallery_image.response_url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:
                                img_url = br_gallery_image.response_url
                            elif br_gallery_image.url:
                                img_url = br_gallery_image.url
                        except Exception:
                            img_url = br_gallery_image.url or ''                        
                    elif br_gallery_image.url:
                        img_url = br_gallery_image.url
                else:
                    res = {}            
                    if br_gallery_image.image:
                        key=hashlib.md5(br_gallery_image.image).hexdigest()
                        if not key:
                            continue
                        if key in gallery_img_keys:
                            continue
                        else:
                            gallery_img_keys.update({key:br_gallery_image.id})
                        res = img_file_upload.upload_image(instance,br_gallery_image.image,"%s_%s_%s"%(odoo_template.name,odoo_template.categ_id.name,odoo_template.id))
                    img_url = res and res.get('id',False) or ''
                if img_url:
                    if instance.is_image_url:
                        tmpl_images.append({'src':img_url,'position': position})
                    else:
                        tmpl_images.append({'id':img_url,'position': position})
                    position += 1
            else:
                if not template.woo_gallery_image_ids:
                    flag = True
            tmpl_images and data.update({"images":tmpl_images})                                                                                                                                                                        
            
            if flag:
                data.update({"images":False})
                flag = False
                
            tmpl_res = wcapi.put('products/%s'%(template.woo_tmpl_id),{'product':data})
            if not isinstance(tmpl_res,requests.models.Response):
                transaction_log_obj.create({'message': "Update Products\nResponse is not in proper format :: %s"%(tmpl_res),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                continue
            if tmpl_res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':tmpl_res.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                continue
            try:            
                response = tmpl_res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While update product image for product with id %s to WooCommerce for instance %s. \n%s"%(template.woo_tmpl_id,instance.name,e),
                             'mismatch_details':True,
                             'type':'product',
                             'woo_instance_id':instance.id
                            })
                continue
            if not isinstance(response, dict):
                transaction_log_obj.create(
                                            {'message':"Update Products\nResponse is not in proper format",
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            errors = response.get('errors','')
            if errors:
                message = errors[0].get('message')
                transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            tmpl_update_response = response.get('product')
            offset = 0
            for tmpl_gallery_image in tmpl_update_response.get('images'):
                tmpl_image_data = {}
                response_image_id = tmpl_gallery_image.get('id')
                response_image_position = tmpl_gallery_image.get('position')
                if not odoo_template.attribute_line_ids and response_image_position == 0:
                    continue                
                if instance.is_image_url:
                    response_image_url = tmpl_gallery_image.get('src')                    
                    tmpl_image_data.update({'response_url':response_image_url})                
                tmpl_image_data.update({'woo_image_id':response_image_id,'sequence':response_image_position})
                woo_product_tmp_img = woo_product_img.search([('woo_product_tmpl_id','=',template.id),('woo_instance_id','=',instance.id)],offset=offset,limit=1)
                woo_product_tmp_img and woo_product_tmp_img.write(tmpl_image_data)
                offset +=1
                
            variant_img_keys = {}
            key = False    
            for variant in template.woo_product_ids:
                if not variant.variant_id or not variant.product_id.attribute_line_ids:
                    continue
                info= {}                
                var_url = ''                
                if instance.is_image_url:                
                    if variant.response_url:
                        try:
                            img = requests.get(variant.response_url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:
                                var_url = variant.response_url
                            elif variant.woo_variant_url or variant.product_id.image_url :
                                var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                        except Exception:
                            var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                    else:
                        var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                else:
                    res = {}
                    if variant.product_id.image:
                        key=hashlib.md5(variant.product_id.image).hexdigest()                                                                          
                        if not key in variant_img_keys:
                            res = img_file_upload.upload_image(instance,variant.product_id.image,"%s_%s"%(variant.name,variant.id))
                            var_url = res and res.get('id',False) or ''
                            variant_img_keys.update({key:var_url})
                        else:
                            var_url = variant_img_keys.get(key)                
                if var_url:
                    if instance.is_image_url:
                        info.update({"images":[{'src':var_url,'position': 0}]})
                    else:
                        info.update({"images":[{'id':var_url,'position': 0}]})
                var_res = wcapi.put('products/%s'%(variant.variant_id),{'product':info})
                if not isinstance(var_res,requests.models.Response):
                    transaction_log_obj.create(
                                                {'message':"Update Product\n Response is not in proper format :: %s"%(var_res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if var_res.status_code not in [200,201]:
                    transaction_log_obj.create(
                                        {'message':var_res.content,
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                try:            
                    var_response =var_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update product image for product with id %s to WooCommerce for instance %s. \n%s"%(template.woo_tmpl_id,instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if not isinstance(var_response, dict):
                    transaction_log_obj.create(
                                                {'message':"Update Product\n Response is not in proper format :: %s"%(var_response),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                errors = var_response.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if instance.is_image_url:
                    update_response =var_response.get('product')
                    update_response_images = update_response.get('images')
                    variant_image_url = update_response_images and update_response_images[0].get('src')
                    variant_image_id = update_response_images and update_response_images[0].get('id')
                    variant.write({'response_url':variant_image_url,'woo_image_id':variant_image_id})                                                 
        return True
                
    @api.model
    def set_new_products_images_in_woo(self,instance):
        transaction_log_obj=self.env['woo.transaction.log']
        woo_templates = self
        wcapi = instance.connect_in_woo()
        batches = []
        woo_template_ids = woo_templates.ids
        total_woo_templates = len(woo_template_ids)
        
        start,end=0,100
        if total_woo_templates > 100:
            while True:                                
                w_template_ids = woo_template_ids[start:end]
                if not w_template_ids:
                    break
                temp=end+100
                start,end = end,temp
                if w_template_ids:
                    w_templates = self.browse(w_template_ids)
                    batches.append(w_templates)
        else:
            batches.append(woo_templates)
                
        for woo_templates in batches:        
            batch_update = {'update':[]}
            batch_update_data = []        
            for template in woo_templates:
                odoo_template = template.product_tmpl_id
                data = {'id':template.woo_tmpl_id,'variations':[]}
                flag= False
                tmpl_images=[]                           
                position = 0
                gallery_img_keys={}
                key = False  
                for br_gallery_image in template.woo_gallery_image_ids:                               
                    img_url = ''
                    if instance.is_image_url:
                        if br_gallery_image.response_url:
                            try:
                                img = requests.get(br_gallery_image.response_url,stream=True,verify=False,timeout=10)
                                if img.status_code == 200:
                                    img_url = br_gallery_image.response_url
                                elif br_gallery_image.url:
                                    img_url = br_gallery_image.url
                            except Exception:
                                img_url = br_gallery_image.url or ''                        
                        elif br_gallery_image.url:
                            img_url = br_gallery_image.url
                    else:
                        res = {}            
                        if br_gallery_image.image:                            
                            key=hashlib.md5(br_gallery_image.image).hexdigest()
                            if not key:
                                continue
                            if key in gallery_img_keys:
                                continue
                            else:
                                gallery_img_keys.update({key:br_gallery_image.id})
                            res = img_file_upload.upload_image(instance,br_gallery_image.image,"%s_%s_%s"%(odoo_template.name,odoo_template.categ_id.name,odoo_template.id))
                        img_url = res and res.get('id',False) or ''
                    if img_url:
                        if instance.is_image_url:
                            tmpl_images.append({'src':img_url,'position': position})
                        else:
                            tmpl_images.append({'id':img_url,'position': position})                    
                        position += 1
                else:
                    data.update({"images":False})
                    flag = True
                    
                if tmpl_images:
                    data.update({"images":tmpl_images})
                    flag = True
                variant_img_keys = {}
                key = False
                
                for variant in template.woo_product_ids:
                    if not variant.variant_id or not variant.product_id.attribute_line_ids:
                        continue                    
                    info= {'id':variant.variant_id}
                    var_url = ''
                    if instance.is_image_url:                
                        if variant.response_url:
                            try:
                                img = requests.get(variant.response_url,stream=True,verify=False,timeout=10)
                                if img.status_code == 200:
                                    var_url = variant.response_url
                                elif variant.woo_variant_url or variant.product_id.image_url :
                                    var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                            except Exception:
                                var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                        else:
                            var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                    else:
                        res = {}
                        if variant.product_id.image:                            
                            key=hashlib.md5(variant.product_id.image).hexdigest()                                                                          
                            if not key in variant_img_keys:                            
                                res = img_file_upload.upload_image(instance,variant.product_id.image,"%s_%s"%(variant.name,variant.id))
                                var_url = res and res.get('id',False) or ''
                                variant_img_keys.update({key:var_url})
                            else:
                                var_url = variant_img_keys.get(key)                                                                  
                
                    if var_url:
                        if instance.is_image_url:
                            info.update({"image":[{'src':var_url,'position': 0}]})
                        else:
                            info.update({"image":[{'id':var_url,'position': 0}]})
                    if template.woo_tmpl_id != variant.variant_id:
                        if instance.is_latest:                                                               
                            info.update({'image':info.get('image') and info.get('image')[0]})
                        data.get('variations').append(info)
                        flag = True
                    elif template.woo_tmpl_id == variant.variant_id:
                        del data['variations']
                        if var_url:
                            if instance.is_image_url:
                                if data.get('images'):
                                    data.get('images').insert(0,{'src':var_url,'position': 0})
                                else:
                                    data.update({'images':[{'src':var_url,'position': 0}]})
                            else:
                                if data.get('images'):
                                    data.get('images').insert(0,{'id':var_url,'position': 0})
                                else:
                                    data.update({'images':[{'id':var_url,'position': 0}]})
                        flag = True
                if instance.is_latest and data.get('variations'):
                    vairant_batches = []
                    start,end=0,100
                    if len(data.get('variations')) > 100:
                        while True:                                
                            w_products_ids = data.get('variations')[start:end]
                            if not w_products_ids:
                                break
                            temp=end+100
                            start,end=end,temp
                            if w_products_ids:
                                vairant_batches.append(w_products_ids)
                    else:
                        vairant_batches.append(data.get('variations'))
                    for woo_variants in vairant_batches:
                        res = wcapi.post('products/%s/variations/batch'%(data.get('id')),{'update':woo_variants})
                        if res.status_code not in [200,201]:
                            transaction_log_obj.create({'message':"Update Product Image\n%s"%(res.content),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                flag and batch_update_data.append(data)
            if batch_update_data:
                batch_update.update({'update':batch_update_data})
                res = wcapi.post('products/batch',batch_update)
                if not isinstance(res,requests.models.Response):               
                    transaction_log_obj.create({'message': "Update Product Image\nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if res.status_code not in [200,201]:
                    transaction_log_obj.create({'message':"Update Product Image\n%s"%(res.content),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                try:            
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update product images to WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if response.get('data',{}) and response.get('data',{}).get('status') != 200:
                    message = response.get('message')
                    transaction_log_obj.create({'message':"Update Product Image\n%s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue        
        return True    
    
    @api.model
    def auto_update_stock_ept(self,ctx={}):
        woo_product_tmpl_obj=self.env['woo.product.template.ept']
        if not isinstance(ctx,dict) or not 'woo_instance_id' in ctx:
            return True
        woo_instance_id = ctx.get('woo_instance_id',False)
        if woo_instance_id:
            woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',woo_instance_id),('exported_in_woo','=',True)])
            instance = self.env['woo.instance.ept'].browse(woo_instance_id)
            if instance and instance.woo_version == 'old':
                self.update_stock_in_woo(instance,woo_templates)
            elif instance and instance.woo_version == 'new':
                self.update_new_stock_in_woo(instance,woo_templates)
        return True            
            
    @api.model
    def update_stock_in_woo(self,instance=False,products=False):
        transaction_log_obj=self.env['woo.transaction.log']
        instances=[]
        if not instance:
            instances=self.env['woo.instance.ept'].search([('stock_auto_export','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:  
            location_ids=instance.warehouse_id.lot_stock_id.child_ids.ids
            location_ids.append(instance.warehouse_id.lot_stock_id.id)
            woo_products = []            
            if not products:
                woo_products=self.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])      
            else:
                woo_products=self.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True),('id','in',products.ids)])      
            if not woo_products:
                continue    
            wcapi = instance.connect_in_woo()
            
            batches = []
            woo_products_ids = woo_products.ids
            total_woo_products = len(woo_products_ids)
            
            start,end=0,100
            if total_woo_products > 100:
                while True:                                
                    w_products_ids = woo_products_ids[start:end]
                    if not w_products_ids:
                        break
                    temp=end+100
                    start,end=end,temp
                    if w_products_ids:
                        woo_products = self.browse(w_products_ids)
                        batches.append(woo_products)
            else:
                batches.append(woo_products)
                    
            for woo_products in batches:            
                batch_update = {'products':[]}
                batch_update_data = []
                for template in woo_products:
                    info = {'id':template.woo_tmpl_id,'variations':[]}
                    flag= False                                                                  
                    for variant in template.woo_product_ids:
                        if variant.variant_id and variant.product_id.type=='product':                        
                            quantity=self.get_stock(variant,instance.warehouse_id.id,instance.stock_field.name)
                            if template.woo_tmpl_id != variant.variant_id:
                                info.get('variations').append({'id':variant.variant_id,'managing_stock':True,'stock_quantity':int(quantity)})
                                flag = True
                            elif template.woo_tmpl_id == variant.variant_id:
                                del info['variations']
                                info.update({'managing_stock':True,'stock_quantity':int(quantity)})
                                flag = True                                                                                             
                    flag and batch_update_data.append(info)
                if batch_update:    
                    batch_update.update({'products':batch_update_data})
                    res = wcapi.post('products/bulk',batch_update)
                    try:            
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While update product stock to WooCommerce for instance %s. \n%s"%(instance.name,e),
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    errors = response.get('errors','')
                    if errors:
                        message = errors[0].get('message')
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'stock',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue                
            if not self._context.get('process')=='update_stock':       
                instance.write({'last_inventory_update_time':datetime.now()})
        return True
    
    @api.model
    def update_new_stock_in_woo(self,instance=False,products=False):
        transaction_log_obj=self.env['woo.transaction.log']
        instances=[]
        if not instance:
            instances=self.env['woo.instance.ept'].search([('stock_auto_export','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:  
            location_ids=instance.warehouse_id.lot_stock_id.child_ids.ids
            location_ids.append(instance.warehouse_id.lot_stock_id.id)
            woo_products = []            
            if not products:
                woo_products=self.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])      
            else:
                woo_products=self.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True),('id','in',products.ids)])      
            if not woo_products:
                continue    
            wcapi = instance.connect_in_woo()
            
            batches = []
            woo_products_ids = woo_products.ids
            total_woo_products = len(woo_products_ids)
            
            start,end=0,100
            if total_woo_products > 100:
                while True:                                
                    w_products_ids = woo_products_ids[start:end]
                    if not w_products_ids:
                        break
                    temp=end+100
                    start,end=end,temp
                    if w_products_ids:
                        woo_products = self.browse(w_products_ids)
                        batches.append(woo_products)
            else:
                batches.append(woo_products)
                    
            for woo_products in batches:            
                batch_update = {'update':[]}
                batch_update_data = []
                for template in woo_products:
                    info = {'id':template.woo_tmpl_id,'variations':[]}
                    flag= False                                                                  
                    for variant in template.woo_product_ids:
                        if variant.variant_id and variant.product_id.type=='product':
                            quantity=self.get_stock(variant,instance.warehouse_id.id,instance.stock_field.name)
                            if template.woo_tmpl_id != variant.variant_id:
                                info.get('variations').append({'id':variant.variant_id,'manage_stock':True,'stock_quantity':int(quantity)})
                                flag = True
                            elif template.woo_tmpl_id == variant.variant_id:
                                del info['variations']
                                info.update({'manage_stock':True,'stock_quantity':int(quantity)})
                                flag = True  
                    if instance.is_latest and info.get('variations'):
                        vairant_batches = []
                        start,end=0,100
                        if len(info.get('variations')) > 100:
                            while True:                                
                                w_products_ids = info.get('variations')[start:end]
                                if not w_products_ids:
                                    break
                                temp=end+100
                                start,end=end,temp
                                if w_products_ids:
                                    vairant_batches.append(w_products_ids)
                        else:
                            vairant_batches.append(info.get('variations'))
                        for woo_variants in vairant_batches:
                            res = wcapi.post('products/%s/variations/batch'%(info.get('id')),{'update':woo_variants})
                            if res.status_code not in [200,201]:
                                transaction_log_obj.create({'message':"Update Product Stock\n%s"%(res.content),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })                                                               
                    flag and batch_update_data.append(info)
                if batch_update_data:
                    batch_update.update({'update':batch_update_data})
                    res = wcapi.post('products/batch',batch_update)
                    if not isinstance(res,requests.models.Response):               
                        transaction_log_obj.create({'message': "Update Product Stock \nResponse is not in proper format :: %s"%(res),
                                                     'mismatch_details':True,
                                                     'type':'stock',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                    if res.status_code not in [200,201]:
                        transaction_log_obj.create(
                                            {'message':res.content,
                                             'mismatch_details':True,
                                             'type':'stock',
                                             'woo_instance_id':instance.id
                                            })
                        continue
                    try:            
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While update product stock to WooCommerce for instance %s. \n%s"%(instance.name,e),
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    if response.get('data',{}) and response.get('data',{}).get('status') != 200:
                        message = response.get('message')
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'stock',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue    
            if not self._context.get('process')=='update_stock':
                instance.write({'last_inventory_update_time':datetime.now()})
        return True    

    @api.model
    def update_price_in_woo(self,instance,woo_templates):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()                     
        for woo_template in woo_templates:                                                                   
            for variant in woo_template.woo_product_ids:
                if  variant.variant_id:                                                      
                    price=instance.pricelist_id.get_product_price(variant.product_id,1.0,partner=False,uom_id=variant.product_id.uom_id.id)                                                                                                                
                    data = {'product':{'regular_price':price,'sale_price':price}}
                    res = wcapi.put('products/%s'%(variant.variant_id),data)
                    if not isinstance(res,requests.models.Response):               
                        transaction_log_obj.create({'message': "Update Product Price \nResponse is not in proper format :: %s"%(res),
                                                     'mismatch_details':True,
                                                     'type':'price',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                    if res.status_code not in [200,201]:
                        transaction_log_obj.create(
                                            {'message':res.content,
                                             'mismatch_details':True,
                                             'type':'price',
                                             'woo_instance_id':instance.id
                                            })
                        continue
                    try:            
                        response = res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While update product price to WooCommerce for instance %s. \n%s"%(instance.name,e),
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue                    
                    errors = response.get('errors','')
                    if errors:
                        message = errors[0].get('message')
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'price',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue                    
        return True
    
    @api.model
    def update_new_price_in_woo(self,instance,woo_templates):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()
        templates = woo_templates
        batches = []
        woo_templates_ids = templates.ids
        total_woo_templates = len(woo_templates_ids)
        
        start,end=0,100
        if total_woo_templates > 100:
            while True:                                
                w_templates_ids = woo_templates_ids[start:end]
                if not w_templates_ids:
                    break
                temp=end+100
                start,end=end,temp
                if w_templates_ids:
                    woo_templates = self.browse(w_templates_ids)
                    batches.append(woo_templates)
        else:
            batches.append(templates)        
        for woo_templates in batches:
            batch_update = {'update':[]}
            batch_update_data = []
            for woo_template in woo_templates:            
                info = {'id':woo_template.woo_tmpl_id,'variations':[]}
                flag= False                                            
                for variant in woo_template.woo_product_ids:
                    if  variant.variant_id:                                                      
                        price=instance.pricelist_id.get_product_price(variant.product_id,1.0,partner=False,uom_id=variant.product_id.uom_id.id)                    
                        if woo_template.woo_tmpl_id != variant.variant_id:
                            info.get('variations').append({'id':variant.variant_id,'regular_price':str(price),'sale_price':str(price)})
                            flag = True
                        elif woo_template.woo_tmpl_id == variant.variant_id:
                            del info['variations']
                            info.update({'regular_price':str(price),'sale_price':str(price)})
                            flag = True 
                if instance.is_latest and info.get('variations'):
                    vairant_batches = []
                    start,end=0,100
                    if len(info.get('variations')) > 100:
                        while True:                                
                            w_products_ids = info.get('variations')[start:end]
                            if not w_products_ids:
                                break
                            temp=end+100
                            start,end=end,temp
                            if w_products_ids:
                                vairant_batches.append(w_products_ids)
                    else:
                        vairant_batches.append(info.get('variations'))
                    for woo_variants in vairant_batches:
                        res = wcapi.post('products/%s/variations/batch'%(info.get('id')),{'update':woo_variants})
                        if res.status_code not in [200,201]:
                            transaction_log_obj.create({'message':"Update Product Price\n%s"%(res.content),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                        })                                                                          
                flag and batch_update_data.append(info)                
            if batch_update_data:
                batch_update.update({'update':batch_update_data})
                res = wcapi.post('products/batch',batch_update)
                if not isinstance(res,requests.models.Response):               
                    transaction_log_obj.create({'message': "Update Product Price \nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'price',
                                                 'woo_instance_id':instance.id
                                                })
                    return True
                if res.status_code not in [200,201]:
                    transaction_log_obj.create(
                                        {'message':res.content,
                                         'mismatch_details':True,
                                         'type':'price',
                                         'woo_instance_id':instance.id
                                        })
                    return True
                try:            
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update product price to WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if response.get('data',{}) and response.get('data',{}).get('status') != 200:
                    message = response.get('message')
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'price',
                                                 'woo_instance_id':instance.id
                                                })
        return True            
            
    @api.multi
    def get_stock(self,woo_product,warehouse_id,stock_type='virtual_available'):
        actual_stock=0.0
        product=self.env['product.product'].with_context(warehouse=warehouse_id).browse(woo_product.product_id.id)
        if stock_type == 'virtual_available':
            if product.virtual_available>0.0:
                actual_stock = product.virtual_available-product.incoming_qty
            else:
                actual_stock=0.0
        else:
            actual_stock = product.qty_available
        if actual_stock >= 1.00:
            if woo_product.fix_stock_type=='fix':
                if woo_product.fix_stock_value >=actual_stock:
                    return actual_stock
                else:
                    return woo_product.fix_stock_value  
                              
            elif woo_product.fix_stock_type == 'percentage':
                quantity = int(actual_stock * woo_product.fix_stock_value)
                if quantity >= actual_stock:
                    return actual_stock
                else:
                    return quantity
        return actual_stock            

    @api.model
    def get_product_attribute(self,template,instance):
        position = 0
        is_variable=False
        attributes=[]
        for attribute_line in template.attribute_line_ids:
            options = []
            for option in attribute_line.value_ids:
                options.append(option.name)
            variation = False
            if attribute_line.attribute_id.create_variant in ['always','dynamic']:
                variation = True
            attribute_data = {'name':attribute_line.attribute_id.name,
                              'slug':attribute_line.attribute_id.name.lower(),
                              'position':position,
                              'visible': True,
                              'variation': variation,
                              'options':options}
            if instance.attribute_type == 'select':
                attrib_data = self.export_product_attributes_in_woo(instance,attribute_line.attribute_id)
                if not attrib_data:
                    break 
                attribute_data.update({'id':attrib_data.get(attribute_line.attribute_id.id)})
            elif instance.attribute_type == 'text':
                attribute_data.update({'name':attribute_line.attribute_id.name})                                    
            position += 1
            if attribute_line.attribute_id.create_variant in ['always','dynamic']:
                is_variable=True
            attributes.append(attribute_data)
        return attributes,is_variable
    
    @api.model
    def get_variant_image(self,instance,variant):
        variant_img_keys = {}
        key = False
        var_url = ''
        variation_data={}
        if instance.is_image_url:                    
            if variant.response_url:
                try:
                    img = requests.get(variant.response_url,stream=True,verify=False,timeout=10)
                    if img.status_code == 200:                                
                        var_url = variant.response_url
                    elif variant.woo_variant_url or variant.product_id.image_url:
                        var_url = variant.woo_variant_url or variant.product_id.image_url or ''                                
                except Exception:
                    var_url = variant.woo_variant_url or variant.product_id.image_url or ''
            elif variant.woo_variant_url or variant.product_id.image_url:
                var_url = variant.woo_variant_url or variant.product_id.image_url or ''
        else:
            res = {}
            if variant.product_id.image:
                key=hashlib.md5(variant.product_id.image).hexdigest()
                if not key in variant_img_keys:
                    res = img_file_upload.upload_image(instance,variant.product_id.image,"%s_%s"%(variant.name,variant.id))
                    var_url = res and res.get('id',False) or ''
                    variant_img_keys.update({key:var_url})
                else:
                    var_url = variant_img_keys.get(key)
        if var_url:
            if instance.is_image_url:
                variation_data.update({"image":[{'src':var_url,'position': 0}]})
            else:
                variation_data.update({"image":[{'id':var_url,'position': 0}]})
        return variation_data
    
    @api.model
    def get_variant_data(self,variant,instance,update_image):
        att = [] 
        woo_attribute_obj=self.env['woo.product.attribute.ept']
        variation_data={}   
        att_data={}                            
        for attribute_value in variant.product_id.attribute_value_ids:
            if instance.attribute_type=='select':
                woo_attribute=woo_attribute_obj.search([('name','=',attribute_value.attribute_id.name),('woo_instance_id','=',instance.id),('exported_in_woo','=',True)],limit=1)
                att_data ={'id':woo_attribute and woo_attribute.woo_attribute_id,'option':attribute_value.name}
            if instance.attribute_type == 'text':
                att_data ={'name':attribute_value.attribute_id.name,'option':attribute_value.name}
            att.append(att_data)
        if update_image:                                        
            variation_data.update(self.get_variant_image(instance, variant))
        variation_data.update({'attributes':att,'sku':str(variant.default_code),'weight':str(variant.product_id.weight)})
        return variation_data
    
    @api.model
    def get_product_price(self,instance,variant):
        price=instance.pricelist_id.get_product_price(variant.product_id,1.0,partner=False,uom_id=variant.product_id.uom_id.id)
        return {'regular_price':str(price),'sale_price':str(price)}
        
    @api.model
    def get_product_stock(self,instance,variant):
        quantity=self.get_stock(variant,instance.warehouse_id.id,instance.stock_field.name)
        return {'manage_stock':True,'stock_quantity':int(quantity)}
    
    @api.model
    def get_gallery_images(self,instance,woo_template,template):
        tmpl_images=[]  
        position = 0
        gallery_img_keys={}
        key = False  
        for br_gallery_image in woo_template.woo_gallery_image_ids:                                
            img_url = ''
            if instance.is_image_url:
                if br_gallery_image.response_url:
                    try:
                        img = requests.get(br_gallery_image.response_url,stream=True,verify=False,timeout=10)
                        if img.status_code == 200:                                
                            img_url = br_gallery_image.response_url
                        elif br_gallery_image.url:
                            img_url = br_gallery_image.url
                    except Exception:
                        img_url = br_gallery_image.url or ''
                elif br_gallery_image.url:
                    img_url = br_gallery_image.url
            else:
                res = {}            
                if br_gallery_image.image:
                    key=hashlib.md5(br_gallery_image.image).hexdigest()
                    if not key:
                        continue
                    if key in gallery_img_keys:
                        continue
                    else:
                        gallery_img_keys.update({key:br_gallery_image.id})
                    res = img_file_upload.upload_image(instance,br_gallery_image.image,"%s_%s_%s"%(template.name,template.categ_id.name,template.id))
                img_url = res and res.get('id',False) or ''
            if img_url:
                if instance.is_image_url:
                    tmpl_images.append({'src':img_url,'position': position})
                else:
                    tmpl_images.append({'id':img_url,'position': position})
                position += 1
        return  tmpl_images
    
    @api.multi
    def get_product_data(self,wcapi,instance,woo_template,publish,update_price,update_stock,update_image,template):
        transaction_log_obj=self.env['woo.transaction.log']
        categ_ids = []
        tag_ids = []
        old = False
        if instance.woo_version=="old":old = True

        description = ''
        short_description = ''
        if woo_template.description:
            woo_template_id = woo_template.with_context(lang=instance.lang_id.code)
            description = woo_template_id.description

        if woo_template.short_description:
            woo_template_id = woo_template.with_context(lang=instance.lang_id.code)
            short_description = woo_template_id.short_description

        data = {'enable_html_description':True,'enable_html_short_description':True,'type': 'simple',
                'title' if old else 'name':woo_template.name,'description':description,'weight':str(template.weight),
                'short_description':short_description,'taxable':woo_template.taxable and 'true' or 'false',
                'shipping_required':'true'}
        for woo_categ in woo_template.woo_categ_ids:
            if not woo_categ.woo_categ_id:
                woo_categ.sync_product_category(instance,woo_product_categ=woo_categ)
                woo_categ.woo_categ_id and categ_ids.append(woo_categ.woo_categ_id)
            else:
                categ_res = wcapi.get("products/categories/%s"%(woo_categ.woo_categ_id))
                if not isinstance(categ_res,requests.models.Response):               
                    transaction_log_obj.create({'message': "Get Product Category \nResponse is not in proper format :: %s"%(categ_res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                try:            
                    categ_res = categ_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import product category from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                woo_product_category = categ_res.get('product_category') if old else categ_res 
                if woo_product_category and woo_product_category.get('id'): 
                    categ_ids.append(woo_categ.woo_categ_id)
                else:
                    woo_categ.sync_product_category(instance,woo_product_categ=woo_categ)
                    woo_categ.woo_categ_id and categ_ids.append(woo_categ.woo_categ_id)
        if categ_ids:
            categ_ids = list(set(categ_ids))
            if not old:
                categ_ids = [{'id': cat_id} for cat_id in categ_ids]
            data.update({'categories':categ_ids})
            
        for woo_tag in woo_template.woo_tag_ids:
            if not woo_tag.woo_tag_id:
                woo_tag.export_product_tags(instance,[woo_tag])
                woo_tag.woo_tag_id and tag_ids.append(woo_tag.woo_tag_id)
            else:
                tag_res = wcapi.get("products/tags/%s"%(woo_tag.woo_tag_id))
                if not isinstance(tag_res,requests.models.Response):               
                    transaction_log_obj.create({'message': "Get Product Tags \nResponse is not in proper format :: %s"%(tag_res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                try:            
                    tag_res = tag_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import product tag from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                woo_product_tag = tag_res.get('product_tag') if old else tag_res 
                if woo_product_tag and woo_product_tag.get('id'):
                    tag_ids.append(woo_tag.woo_tag_id)
                else:                         
                    woo_tag.export_product_tags(instance,[woo_tag])
                    woo_tag.woo_tag_id and tag_ids.append(woo_tag.woo_tag_id)
                
        if tag_ids:
            tag_ids = list(set(tag_ids))
            if not old:
                tag_ids = [{'id': tag_id} for tag_id in tag_ids]
            data.update({'tags': tag_ids})
        
        if publish:
            data.update({'status':'publish'})                
        else:
            data.update({'status':'draft'})
        
        attributes,is_variable = self.get_product_attribute(template,instance)
        if is_variable:
            data.update({'type':'variable'})
                                       
        if template.attribute_line_ids:                                               
            variations = []
            default_att = []
            for variant in woo_template.woo_product_ids:                
                variation_data = {}
                product_variant=self.get_variant_data(variant,instance,update_image)
                variation_data.update(product_variant)                   
                if update_price:                     
                    if data.get('type')=='simple':
                        data.update(self.get_product_price(instance, variant))
                    else:
                        variation_data.update(self.get_product_price(instance, variant))
                if update_stock:                        
                    if data.get('type')=='simple':
                        data.update(self.get_product_stock(instance, variant))
                    else:
                        variation_data.update(self.get_product_stock(instance, variant))
                variations.append(variation_data)
            default_att =  variations and variations[0].get('attributes') or []
            data.update({'attributes':attributes,'default_attributes':default_att,'variations':variations})
            if data.get('type')=='simple':
                data.update({'sku':str(variant.default_code)})
        else:
            variant = woo_template.woo_product_ids
            data.update(self.get_variant_data(variant,instance,update_image))
            if update_price:
                data.update(self.get_product_price(instance, variant))
            if update_stock:                        
                data.update(self.get_product_stock(instance, variant))
        
        tmpl_images=[]                
        if update_image:
            tmpl_images=self.get_gallery_images(instance, woo_template, template)
            tmpl_images and data.update({"images":tmpl_images})
        return data
    
    @api.multi
    def get_product_update_data(self,wcapi,template,instance,update_image):
        transaction_log_obj=self.env['woo.transaction.log']
        categ_ids = []
        tag_ids = []

        description = ''
        short_description = ''
        if template.description:
            woo_template_id = template.with_context(lang=instance.lang_id.code)
            description = woo_template_id.description

        if template.short_description:
            woo_template_id = template.with_context(lang=instance.lang_id.code)
            short_description = woo_template_id.short_description

        data = {'id':template.woo_tmpl_id,'variations':[],'name':template.name,'enable_html_description':True,
                'enable_html_short_description':True,'description':description,
                'short_description':short_description,'weight':str(template.product_tmpl_id.weight),
                'taxable':template.taxable and 'true' or 'false'}
        flag= False
        tmpl_images=[]
        if update_image:
            tmpl_images=self.get_gallery_images(instance, template, template.product_tmpl_id)
            data.update({"images":tmpl_images})
            flag=True
        for woo_categ in template.woo_categ_ids:
            if not woo_categ.woo_categ_id:                    
                woo_categ.sync_product_category(instance,woo_product_categ=woo_categ)
                woo_categ.woo_categ_id and categ_ids.append(woo_categ.woo_categ_id)
            else:
                categ_res = wcapi.get("products/categories/%s"%(woo_categ.woo_categ_id))
                if not isinstance(categ_res,requests.models.Response):
                    transaction_log_obj.create({'message':"Get Product Category \n Response is not in proper format :: %s"%(categ_res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                try:            
                    woo_product_category = categ_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import product category from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if woo_product_category.get('id'): 
                    categ_ids.append(woo_categ.woo_categ_id)
                else:
                    woo_categ.export_product_categs(instance,[woo_categ])
                    woo_categ.woo_categ_id and categ_ids.append(woo_categ.woo_categ_id)
        if categ_ids:
            categ_ids = list(set(categ_ids))
            categ_ids = [{'id':cat_id} for cat_id in categ_ids]
            data.update({'categories':categ_ids})
            
        for woo_tag in template.woo_tag_ids:
            if not woo_tag.woo_tag_id:
                woo_tag.export_product_tags(instance,[woo_tag])
                woo_tag.woo_tag_id and tag_ids.append(woo_tag.woo_tag_id)
            else:
                tag_res = wcapi.get("products/tags/%s"%(woo_tag.woo_tag_id))
                if not isinstance(tag_res,requests.models.Response):
                    transaction_log_obj.create({'message':"Get Product Tags \n Response is not in proper format :: %s"%(tag_res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                try:            
                    woo_product_tag = tag_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import product tag from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if woo_product_tag.get('id'):
                    tag_ids.append(woo_tag.woo_tag_id)
                else:                         
                    woo_tag.export_product_tags(instance,[woo_tag])
                    woo_tag.woo_tag_id and tag_ids.append(woo_tag.woo_tag_id)
                
        if tag_ids:
            tag_ids = list(set(tag_ids))
            tag_ids = [{'id':tag_id} for tag_id in tag_ids]
            data.update({'tags':tag_ids})
        
        for variant in template.woo_product_ids:
            if not variant.variant_id:
                continue
            info= {}
            info.update({'id':variant.variant_id,'weight':str(variant.product_id.weight)})
            var_url = ''
            if update_image:                        
                info.update(self.get_variant_image(instance, variant))
            if template.woo_tmpl_id != variant.variant_id:                                                               
                data.get('variations').append(info)
                flag = True
            elif template.woo_tmpl_id == variant.variant_id:
                del data['variations']
                if var_url:
                    if instance.is_image_url:
                        if data.get('images'):
                            data.get('images').insert(0,{'src':var_url,'position': 0})
                        else:
                            data.update({'images':[{'src':var_url,'position': 0}]})
                    else:
                        if data.get('images'):
                            data.get('images').insert(0,{'id':var_url,'position': 0})
                        else:
                            data.update({'images':[{'id':var_url,'position': 0}]})
                flag = True
        if instance.is_latest and not template.woo_tmpl_id == variant.variant_id:
            vairant_batches = []
            start,end=0,100
            if len(data.get('variations')) > 100:
                while True:                                
                    w_products_ids = data.get('variations')[start:end]
                    if not w_products_ids:
                        break
                    temp=end+100
                    start,end=end,temp
                    if w_products_ids:
                        vairant_batches.append(w_products_ids)
            else:
                vairant_batches.append(data.get('variations'))
            for woo_variants in vairant_batches:
                res = wcapi.post('products/%s/variations/batch'%(template.woo_tmpl_id),{'update':(woo_variants)})
                if res.status_code not in [200,201]:
                    transaction_log_obj.create({'message':"Update Product Error\n%s"%(res.content),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
        return flag,data
    
    @api.model
    def update_products_in_woo(self,instance,templates,update_image):
        transaction_log_obj=self.env['woo.transaction.log']
        woo_product_img = self.env['woo.product.image.ept']
        wcapi = instance.connect_in_woo()
        for template in templates:
            categ_ids = []
            tag_ids = []
            odoo_template = template.product_tmpl_id                                         
            
            data = {'title':template.name,'enable_html_description':True,'enable_html_short_description':True,'description':template.description or '',
                    'weight':template.product_tmpl_id.weight,'short_description':template.short_description or '','taxable':template.taxable and 'true' or 'false'}
            
            tmpl_images=[]                           
            position = 0
            
            if not odoo_template.attribute_line_ids and template.woo_tmpl_id == template.woo_product_ids[0].variant_id:
                position = 1
            if update_image:
                gallery_img_keys={}
                key = False    
                for br_gallery_image in template.woo_gallery_image_ids:                               
                    img_url = ''
                    if instance.is_image_url:
                        if br_gallery_image.response_url:
                            try:
                                img = requests.get(br_gallery_image.response_url,stream=True,verify=False,timeout=10)
                                if img.status_code == 200:
                                    img_url = br_gallery_image.response_url
                                elif br_gallery_image.url:
                                    img_url = br_gallery_image.url
                            except Exception:
                                img_url = br_gallery_image.url or ''                        
                        elif br_gallery_image.url:
                            img_url = br_gallery_image.url
                    else:
                        res = {}            
                        if br_gallery_image.image:
                            key=hashlib.md5(br_gallery_image.image).hexdigest()
                            if not key:
                                continue
                            if key in gallery_img_keys:
                                continue
                            else:
                                gallery_img_keys.update({key:br_gallery_image.id})
                            res = img_file_upload.upload_image(instance,br_gallery_image.image,"%s_%s_%s"%(odoo_template.name,odoo_template.categ_id.name,odoo_template.id))
                        img_url = res and res.get('id',False) or ''
                    if img_url:
                        if instance.is_image_url:
                            tmpl_images.append({'src':img_url,'position': position})
                        else:
                            tmpl_images.append({'id':img_url,'position': position})
                        position += 1
            tmpl_images and data.update({"images":tmpl_images})                                                                   
            for woo_categ in template.woo_categ_ids:
                if not woo_categ.woo_categ_id:                    
                    woo_categ.sync_product_category(instance,woo_product_categ=woo_categ)
                    woo_categ.woo_categ_id and categ_ids.append(woo_categ.woo_categ_id)
                else:
                    categ_res = wcapi.get("products/categories/%s"%(woo_categ.woo_categ_id))
                    if not isinstance(categ_res,requests.models.Response):               
                        transaction_log_obj.create({'message': "Get Product Category\nResponse is not in proper format :: %s"%(categ_res),
                                                     'mismatch_details':True,
                                                     'type':'product',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                    try:            
                        categ_res = categ_res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While import product category from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    woo_product_category = categ_res.get('product_category')
                    if woo_product_category.get('id'): 
                        categ_ids.append(woo_categ.woo_categ_id)
                    else:
                        woo_categ.export_product_categs(instance,[woo_categ])
                        woo_categ.woo_categ_id and categ_ids.append(woo_categ.woo_categ_id)
            if categ_ids:
                data.update({'categories':list(set(categ_ids))})
                
            for woo_tag in template.woo_tag_ids:
                if not woo_tag.woo_tag_id:
                    woo_tag.export_product_tags(instance,[woo_tag])
                    woo_tag.woo_tag_id and tag_ids.append(woo_tag.woo_tag_id)
                else:
                    tag_res = wcapi.get("products/tags/%s"%(woo_tag.woo_tag_id))
                    if not isinstance(tag_res,requests.models.Response):               
                        transaction_log_obj.create({'message': "Get Product Tags\nResponse is not in proper format :: %s"%(tag_res),
                                                     'mismatch_details':True,
                                                     'type':'product',
                                                     'woo_instance_id':instance.id
                                                    })
                        continue
                    try:            
                        tag_res = tag_res.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While import product tag from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    woo_product_tag = tag_res.get('product_tag')
                    if woo_product_tag.get('id'):
                        tag_ids.append(woo_tag.woo_tag_id)
                    else:                         
                        woo_tag.export_product_tags(instance,[woo_tag])
                        woo_tag.woo_tag_id and tag_ids.append(woo_tag.woo_tag_id)
                    
            if tag_ids:
                data.update({'tags':list(set(tag_ids))})                                                               
            
            tmpl_res = wcapi.put('products/%s'%(template.woo_tmpl_id),{'product':data})
            if not isinstance(tmpl_res,requests.models.Response):
                transaction_log_obj.create({'message': "Update Products\nResponse is not in proper format :: %s"%(tmpl_res),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                continue
            if tmpl_res.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':tmpl_res.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                continue
            try:            
                response = tmpl_res.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While update product with id %s to WooCommerce for instance %s. \n%s"%(template.woo_tmpl_id,instance.name,e),
                             'mismatch_details':True,
                             'type':'product',
                             'woo_instance_id':instance.id
                            })
                continue
            if not isinstance(response, dict):
                transaction_log_obj.create(
                                            {'message':"Update Products\nResponse is not in proper format",
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            errors = response.get('errors','')
            if errors:
                message = errors[0].get('message')
                transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            tmpl_update_response = response.get('product')
            offset = 0
            for tmpl_gallery_image in tmpl_update_response.get('images'):
                tmpl_image_data = {}
                response_image_id = tmpl_gallery_image.get('id')
                response_image_position = tmpl_gallery_image.get('position')
                if not odoo_template.attribute_line_ids and response_image_position == 0:
                    continue                
                if instance.is_image_url:
                    response_image_url = tmpl_gallery_image.get('src')                    
                    tmpl_image_data.update({'response_url':response_image_url})                
                tmpl_image_data.update({'woo_image_id':response_image_id,'sequence':response_image_position})
                woo_product_tmp_img = woo_product_img.search([('woo_product_tmpl_id','=',template.id),('woo_instance_id','=',instance.id)],offset=offset,limit=1)
                woo_product_tmp_img and woo_product_tmp_img.write(tmpl_image_data)
                offset +=1
                
            variant_img_keys = {}
            key = False    
            for variant in template.woo_product_ids:
                if not variant.variant_id:
                    continue
                info= {}
                info.update({'sku':variant.default_code,'weight':variant.product_id.weight})
                var_url = ''
                if update_image:
                    if instance.is_image_url:                
                        if variant.response_url:
                            try:
                                img = requests.get(variant.response_url,stream=True,verify=False,timeout=10)
                                if img.status_code == 200:
                                    var_url = variant.response_url
                                elif variant.woo_variant_url or variant.product_id.image_url :
                                    var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                            except Exception:
                                var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                        else:
                            var_url = variant.woo_variant_url or variant.product_id.image_url or ''
                    else:
                        res = {}
                        if variant.product_id.image:
                            key=hashlib.md5(variant.product_id.image).hexdigest()                                                                          
                            if not key in variant_img_keys:
                                res = img_file_upload.upload_image(instance,variant.product_id.image,"%s_%s"%(variant.name,variant.id))
                                var_url = res and res.get('id',False) or ''
                                variant_img_keys.update({key:var_url})
                            else:
                                var_url = variant_img_keys.get(key)                
                if var_url:
                    if instance.is_image_url:
                        info.update({"images":[{'src':var_url,'position': 0}]})
                    else:
                        info.update({"images":[{'id':var_url,'position': 0}]})
                var_res = wcapi.put('products/%s'%(variant.variant_id),{'product':info})
                if not isinstance(var_res,requests.models.Response):
                    transaction_log_obj.create(
                                                {'message':"Update Product\n Response is not in proper format :: %s"%(var_res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if var_res.status_code not in [200,201]:
                    transaction_log_obj.create(
                                        {'message':var_res.content,
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                try:            
                    var_response = var_res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update product with id %s to WooCommerce for instance %s. \n%s"%(template.woo_tmpl_id,instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if not isinstance(var_response, dict):
                    transaction_log_obj.create(
                                                {'message':"Update Product\n Response is not in proper format :: %s"%(var_response),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                errors = var_response.get('errors','')
                if errors:
                    message = errors[0].get('message')
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if instance.is_image_url:
                    update_response =var_response.get('product')
                    update_response_images = update_response.get('images')
                    variant_image_url = update_response_images and update_response_images[0].get('src')
                    variant_image_id = update_response_images and update_response_images[0].get('id')
                    variant.write({'response_url':variant_image_url,'woo_image_id':variant_image_id})                                                 
        return True

    @api.model
    def update_new_products_in_woo(self,instance,templates,update_image):
        transaction_log_obj=self.env['woo.transaction.log']                              
        wcapi = instance.connect_in_woo()
        
        batches = []
        woo_templates_ids = templates.ids
        total_woo_templates = len(woo_templates_ids)
        
        start,end=0,100
        if total_woo_templates > 100:
            while True:                                
                w_templates_ids = woo_templates_ids[start:end]
                if not w_templates_ids:
                    break
                temp=end+100
                start,end=end,temp
                if w_templates_ids:
                    woo_templates = self.browse(w_templates_ids)
                    batches.append(woo_templates)
        else:
            batches.append(templates)
                
        for templates in batches:                
            batch_update = {'update':[]}
            batch_update_data = []
        
            for template in templates:
                flag,data=self.get_product_update_data(wcapi, template, instance, update_image)
                flag and batch_update_data.append(data)
            if batch_update_data:
                batch_update.update({'update':batch_update_data})
                res = wcapi.post('products/batch',batch_update)
                if not isinstance(res,requests.models.Response):               
                    transaction_log_obj.create({'message': "Update Product \nResponse is not in proper format :: %s"%(res),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue
                if res.status_code not in [200,201]:
                    transaction_log_obj.create(
                                        {'message':"Update Product \n%s"%(res.content),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                try:            
                    response = res.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While update products to WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                if response.get('data',{}) and response.get('data',{}).get('status') != 200:
                    message = response.get('message')
                    transaction_log_obj.create(
                                                {'message':"Update Product \n%s"%(message),
                                                 'mismatch_details':True,
                                                 'type':'product',
                                                 'woo_instance_id':instance.id
                                                })
                    continue  
        return True
    
    @api.model
    def export_products_in_woo(self,instance,woo_templates,update_price,update_stock,publish,update_image):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()        
        woo_product_product_ept = self.env['woo.product.product.ept']
        woo_product_img = self.env['woo.product.image.ept']
        
        for woo_template in woo_templates:
            template = woo_template.product_tmpl_id
            data = self.get_product_data(wcapi,instance, woo_template, publish, update_price, update_stock, update_image, template)                                                                                                                       
            new_product = wcapi.post('products',{'product':data})
            if not isinstance(new_product,requests.models.Response):               
                transaction_log_obj.create({'message': "Export Product \nResponse is not in proper format :: %s"%(new_product),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if new_product.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':new_product.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                continue
            try:            
                response = new_product.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While export product to WooCommerce for instance %s. \n%s"%(instance.name,e),
                             'mismatch_details':True,
                             'type':'product',
                             'woo_instance_id':instance.id
                            })
                continue
            if not isinstance(response, dict):
                transaction_log_obj.create({'message':"Response is not in proper format :: %s"%(response),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            errors = response.get('errors','')
            if errors:
                message = errors[0].get('message')
                code = errors[0].get('code')
                if code == 'woocommerce_api_product_sku_already_exists':
                    message = "%s, SKU ==> %s"%(message,data.get('title')) 
                transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            response = response.get('product')
            response_variations = response.get('variations')
            for response_variation in response_variations:
                response_variant_data = {}
                variant_sku = response_variation.get('sku')
                variant_id = response_variation.get('id')
                if instance.is_image_url:
                    variant_image = response_variation.get('image')
                    variant_image_id = variant_image and variant_image.get('id') or False
                    variant_image_url = variant_image and variant_image.get('src') or ''
                    response_variant_data.update({'woo_image_id':variant_image_id,'response_url':variant_image_url})
                variant_created_at = response_variation.get('created_at')
                variant_updated_at = response_variation.get('updated_at')
                if variant_created_at.startswith('-'):
                    variant_created_at = variant_created_at[1:]                 
                if variant_updated_at.startswith('-'):
                    variant_updated_at = variant_updated_at[1:]
                woo_product = woo_product_product_ept.search([('default_code','=',variant_sku),('woo_template_id','=',woo_template.id),('woo_instance_id','=',instance.id)])
                response_variant_data.update({'variant_id':variant_id,'created_at':variant_created_at,'updated_at':variant_updated_at,'exported_in_woo':True})
                woo_product and woo_product.write(response_variant_data) 
            woo_tmpl_id = response.get('id')
            tmpl_images = response.get('images')
            offset = 0
            for tmpl_image in tmpl_images:
                tmpl_image_data = {}
                img_id = tmpl_image.get('id')
                position = tmpl_image.get('position')
                if not template.attribute_line_ids and position == 0:
                    continue
                if instance.is_image_url:                                                       
                    res_img_url = tmpl_image.get('src')
                    tmpl_image_data.update({'response_url':res_img_url})                
                tmpl_image_data.update({'woo_image_id':img_id,'sequence':position})
                self._cr.execute("select id from woo_product_image_ept where woo_product_tmpl_id='%s' and woo_instance_id='%s' limit 1 offset '%s'"%(woo_template.id,instance.id,offset))
                image_id = self._cr.fetchall()
                if image_id and isinstance(image_id,list):
                    woo_product_tmp_img = woo_product_img.browse(image_id[0][0])
                    woo_product_tmp_img.write(tmpl_image_data)
                offset +=1
            created_at = response.get('created_at')
            updated_at = response.get('updated_at')
            if created_at.startswith('-'):
                created_at = created_at[1:]                 
            if updated_at.startswith('-'):
                updated_at = updated_at[1:]
            if not template.attribute_line_ids:
                woo_product = woo_template.woo_product_ids
                woo_product.write({'variant_id':woo_tmpl_id,'created_at':created_at,'updated_at':updated_at,'exported_in_woo':True})
            tmpl_data= {'woo_tmpl_id':woo_tmpl_id,'created_at':created_at,'updated_at':updated_at,'exported_in_woo':True}
            tmpl_data.update({'website_published':True}) if publish else tmpl_data.update({'website_published':False})
            woo_template.write(tmpl_data)
            self.sync_woo_attribute_term(instance)
            self._cr.commit()
        return True
        
    @api.model
    def export_new_products_in_woo(self,instance,woo_templates,update_price,update_stock,publish,update_image):
        transaction_log_obj=self.env['woo.transaction.log']
        wcapi = instance.connect_in_woo()        
        woo_product_product_ept = self.env['woo.product.product.ept']
        woo_product_img = self.env['woo.product.image.ept']
        variants=[]
        for woo_template in woo_templates:
            template = woo_template.product_tmpl_id
            data=self.get_product_data(wcapi,instance, woo_template, publish, update_price, update_stock, update_image, template)
            if instance.is_latest:
                variants=data.get('variations') or []
                variants and data.update({'variations':[]})
            new_product = wcapi.post('products',data)
            if not isinstance(new_product,requests.models.Response):               
                transaction_log_obj.create({'message': "Export Product\nResponse is not in proper format :: %s"%(new_product),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if new_product.status_code not in [200,201]:
                transaction_log_obj.create(
                                    {'message':new_product.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                continue
            try:            
                response = new_product.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While export product to WooCommerce for instance %s. \n%s"%(instance.name,e),
                             'mismatch_details':True,
                             'type':'product',
                             'woo_instance_id':instance.id
                            })
                continue
            if response.get('data',{}) and response.get('data',{}).get('status') not in [200,201]:
                message = response.get('message')
                if response.get('code') == 'woocommerce_rest_product_sku_already_exists':                   
                    message = "%s, ==> %s"%(message,data.get('name'))
                transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue
            if not isinstance(response, dict):
                transaction_log_obj.create(
                                            {'message':"Export Product, Response is not in proper format",
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                continue           
            response_variations=[]           
            if not instance.is_latest:
                response_variations = response.get('variations')
            woo_tmpl_id = response.get('id') or False
            
            if woo_tmpl_id and instance.is_latest and variants:
                response_variations=[]
                vairant_batches = []
                start,end=0,100
                if len(variants) > 100:
                    while True:                                
                        w_products_ids = variants[start:end]
                        if not w_products_ids:
                            break
                        temp=end+100
                        start,end=end,temp
                        if w_products_ids:
                            vairant_batches.append(w_products_ids)
                else:
                    vairant_batches.append(variants)
                for woo_variants in vairant_batches:
                    for variant in woo_variants:
                        if variant.get('image'):
                            variant.update({'image':variant.get('image')[0]})
                    variant_response=wcapi.post("products/%s/variations/batch"%(woo_tmpl_id),{'create':woo_variants})
                    if variant_response.status_code not in [200,201]:
                        transaction_log_obj.create(
                                    {'message':variant_response.content,
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    try:            
                        response_variations+=variant_response.json().get('create')
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While retrive product response from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                     'mismatch_details':True,
                                     'type':'product',
                                     'woo_instance_id':instance.id
                                    })
                        continue
            
            for response_variation in response_variations:
                if response_variation.get('error'):
                    transaction_log_obj.create(
                                {'message':response_variation.get('error'),
                                 'mismatch_details':True,
                                 'type':'product',
                                 'woo_instance_id':instance.id
                                })
                    continue
                response_variant_data = {}
                variant_sku = response_variation.get('sku')
                variant_id = response_variation.get('id')
                if instance.is_image_url:
                    variant_image = response_variation.get('image')
                    variant_image_id = variant_image and variant_image.get('id') or False
                    variant_image_url = variant_image and variant_image.get('src') or ''
                    response_variant_data.update({'woo_image_id':variant_image_id,'response_url':variant_image_url})
                variant_created_at = response_variation.get('date_created')
                variant_updated_at = response_variation.get('date_modified')
                if variant_created_at.startswith('-'):
                    variant_created_at = variant_created_at[1:]                 
                if variant_updated_at.startswith('-'):
                    variant_updated_at = variant_updated_at[1:]
                woo_product = woo_product_product_ept.search([('default_code','=',variant_sku),('woo_template_id','=',woo_template.id),('woo_instance_id','=',instance.id)])
                response_variant_data.update({'variant_id':variant_id,'created_at':variant_created_at,'updated_at':variant_updated_at,'exported_in_woo':True})
                woo_product and woo_product.write(response_variant_data) 
            woo_tmpl_id = response.get('id')
            tmpl_images = response.get('images')
            offset = 0
            for tmpl_image in tmpl_images:
                tmpl_image_data = {}
                img_id = tmpl_image.get('id')
                position = tmpl_image.get('position')
                if not template.attribute_line_ids and position == 0:
                    continue
                if instance.is_image_url:                                                       
                    res_img_url = tmpl_image.get('src')
                    tmpl_image_data.update({'response_url':res_img_url})                
                tmpl_image_data.update({'woo_image_id':img_id,'sequence':position})
                woo_product_tmp_img = woo_product_img.search([('woo_product_tmpl_id','=',woo_template.id),('woo_instance_id','=',instance.id)],offset=offset,limit=1)                
                woo_product_tmp_img and woo_product_tmp_img.write(tmpl_image_data)
                offset +=1
            created_at = response.get('date_created')
            updated_at = response.get('date_modified')
            if created_at and created_at.startswith('-'):
                created_at = created_at[1:]                 
            if updated_at and updated_at.startswith('-'):
                updated_at = updated_at[1:]
            if template.product_variant_count==1:
                woo_product = woo_template.woo_product_ids
                woo_product.write({'variant_id':woo_tmpl_id,'created_at':created_at or False,'updated_at':updated_at or False,'exported_in_woo':True})
            total_variants_in_woo=response.get('variations') and len(response.get('variations')) or 1
            tmpl_data= {'woo_tmpl_id':woo_tmpl_id,'created_at':created_at or False,'updated_at':updated_at or False,'exported_in_woo':True,'total_variants_in_woo':total_variants_in_woo}
            tmpl_data.update({'website_published':True}) if publish else tmpl_data.update({'website_published':False})
            woo_template.write(tmpl_data)
            self.sync_woo_attribute_term(instance)
            self._cr.commit()
        return True    
    
class woo_product_product_ept(models.Model):
    _name="woo.product.product.ept"
    _order='product_id'
    _description = "WooCommerce Product"
    
    @api.one
    def set_image(self):
        for variant_image in self:
            if variant_image.woo_instance_id.is_image_url:
                if variant_image.response_url:
                    try:  
                        img = requests.get(variant_image.response_url,stream=True,verify=False,timeout=10)
                        if img.status_code == 200:                        
                            variant_image.url_image=base64.b64encode(img.content)
                        else:
                            img = requests.get(variant_image.woo_variant_url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:                        
                                variant_image.url_image=base64.b64encode(img.content)
                    except Exception:
                        try:  
                            img = requests.get(variant_image.woo_variant_url,stream=True,verify=False,timeout=10)
                            variant_image.url_image=base64.b64encode(img.content)
                        except Exception:
                            pass
                
                elif variant_image.woo_variant_url:          
                    try:  
                        img = requests.get(variant_image.woo_variant_url,stream=True,verify=False,timeout=10)
                        if img.status_code == 200:
                            variant_image.url_image=base64.b64encode(img.content)
                    except Exception:
                        pass          
    producturl=fields.Text("Product URL")
    name=fields.Char("Title")    
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",required=1)
    default_code=fields.Char("Default Code")
    product_id=fields.Many2one("product.product","Product",required=1)
    woo_template_id=fields.Many2one("woo.product.template.ept","Woo Template",required=1,ondelete="cascade")
    exported_in_woo=fields.Boolean("Exported In Woo")
    variant_id=fields.Char("Variant Id")
    fix_stock_type =  fields.Selection([('fix','Fix'),('percentage','Percentage')], string='Fix Stock Type')
    fix_stock_value = fields.Float(string='Fix Stock Value',digits=dp.get_precision("Product UoS"))
    created_at=fields.Datetime("Created At")
    updated_at=fields.Datetime("Updated At")
    is_image_url=fields.Boolean("Is Image Url ?",related="woo_instance_id.is_image_url")
    woo_variant_url = fields.Char(size=600, string='Image URL')
    response_url = fields.Char(size=600, string='Response URL',help="URL from WooCommerce")
    url_image=fields.Binary("Image",compute=set_image,store=False)
    woo_image_id=fields.Char("Image Id",help="WooCommerce Image Id")
