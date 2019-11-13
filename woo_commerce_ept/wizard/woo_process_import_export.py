from odoo import models, fields, api
from odoo.exceptions import Warning
from _collections import OrderedDict
from _datetime import datetime
from datetime import datetime

class woo_process_import_export(models.TransientModel):
    _name = 'woo.process.import.export'   
    _description = "WooCommerce Import/Export Process"
    
    instance_ids = fields.Many2many("woo.instance.ept",'woo_instance_import_export_rel','process_id','woo_instance_id',"Instances")
    
    update_price_in_product=fields.Boolean("Set Price",default=False)
    update_stock_in_product=fields.Boolean("Set Stock",default=False)
    publish=fields.Boolean("Publish In Website",default=False)
    update_image_in_product_export=fields.Boolean("Set Image in Woocommerce",default=False)

    is_export_products=fields.Boolean("Export Products",help="Export Products that are prepared for Woo Export.")    
    sync_product_from_woo=fields.Boolean("Sync Products")
    
    is_publish_products=fields.Boolean("Publish Products",help="Publish all products that are exported.")
    is_unpublish_products=fields.Boolean("UnPublish Products",help="Unpublish all products that are exported and published.")
    
    is_update_products=fields.Boolean("Update Products",help="Update product details of products that are already exported.")
    update_image_in_product_update=fields.Boolean("Set Image",default=False)
        
    is_update_stock=fields.Boolean("Update Stock",help="Update Stock Level from Odoo to WooCommerce.")
    is_update_price=fields.Boolean("Update Price",help="Update price of products from Odoo to WooCommerce.")
    is_update_image=fields.Boolean("Update Images",help="Update product images from Odoo to WooCommerce.")     
    
    is_import_orders=fields.Boolean("Import Orders")
    is_import_customers=fields.Boolean("Import Customers")
    is_update_order_status=fields.Boolean("Update Order Status",help="Update order status in WooCommerce if it is changed in Odoo.")
    
    is_export_product_tags=fields.Boolean("Export Product Tags",help="Export newly created product tags to WooCommerce.")
    is_update_product_tags=fields.Boolean("Update Product Tags")
    
    is_export_product_categ=fields.Boolean("Export Product Category",help="Export newly created product categories to WooCommerce.")
    is_update_product_categ=fields.Boolean("Update Product Category")
    sync_product_category_from_woo=fields.Boolean("Sync Product Category")    
    sync_product_tags_from_woo=fields.Boolean("Sync Product Tags")
    
    sync_woo_coupons=fields.Boolean("Sync Coupons")
    is_export_coupons=fields.Boolean("Export Coupons",help="Export newly created coupons to WooCommerce.")
    is_update_coupon=fields.Boolean("Update Coupons",help="Update coupons created in Odoo to WooCommerce.")
    sync_images_with_product=fields.Boolean("Sync Images?",help="Check if you want to import images along with products",default=False)
    sync_price_with_product=fields.Boolean("Sync Product Price?",help="Check if you want to import price along with products",default=False)
    is_import_stock=fields.Boolean("Import Stock",default=False)
    sync_attributes=fields.Boolean("Sync Attributes",help="Import or Sync WooCommerce Atrributes and its Terms.",default=False)
    #Add by Haresh Mori,This is use for import order date wise from woo commerce   
    past_orders_before_date=fields.Datetime(string="To")
    past_orders_after_date=fields.Datetime(string="From")
    

    is_skip_sync_existing_product = fields.Boolean(string="Skip Existing Product?",
                                                  help="Do You Want Skip Existing Product Imported From WooCommerce?")

    @api.onchange("sync_product_from_woo")
    def onchange_sync_product(self):
        for record in self:
            if not record.sync_product_from_woo:
                record.is_skip_sync_existing_product = False

    @api.model
    def default_get(self,fields):
        res = super(woo_process_import_export,self).default_get(fields)
        if 'default_instance_id' in self._context:
            res.update({'instance_ids':[(6,0,[self._context.get('default_instance_id')])]})
            woo_instance = self._context.get('default_instance_id')
            woo_instance = self.env['woo.instance.ept'].search([('id','=',woo_instance)],limit = 1)
            past_orders_before_date = str(datetime.now())
            past_orders_after_date = woo_instance.last_synced_order_date
            if woo_instance:
                res.update({'past_orders_before_date':past_orders_before_date,'past_orders_after_date':past_orders_after_date})
        elif 'instance_ids' in fields:
            instances = self.env['woo.instance.ept'].search([('state','=','confirmed')])
            res.update({'instance_ids':[(6,0,instances.ids)]})
            past_orders_before_date = str(datetime.now())
            past_orders_after_date = instances and instances[0].last_synced_order_date
            if instances:
                res.update({'past_orders_before_date':past_orders_before_date,'past_orders_after_date':past_orders_after_date})
        return res
    
    @api.multi
    def execute(self):
        if self.is_export_products:
            self.export_products()
        if self.is_update_products:
            self.update_products()
        if self.is_update_price:
            self.update_price()
        if self.is_update_stock:
            self.update_stock_in_woo()
        if self.is_update_image:
            self.set_product_images()            
        if self.is_publish_products:
            self.publish_multiple_products()
        if self.is_unpublish_products:
            self.unpublish_multiple_products()    
        if self.sync_product_from_woo:
            self.sync_products()
        if self.is_import_orders:
            self.import_sale_orders()
        if self.is_import_customers:
            self.import_woo_customers()
        if self.is_update_order_status:
            self.update_order_status()
        if self.is_export_product_tags:
            self.export_product_tags()
        if self.is_update_product_tags:
            self.update_product_tags()
        if self.is_export_product_categ:
            self.export_product_categ()
        if self.is_update_product_categ:
            self.update_product_categ()
        if self.sync_product_category_from_woo:
            self.sync_product_category()
        if self.sync_product_tags_from_woo:
            self.sync_product_tags()
        if self.sync_woo_coupons:
            self.sync_coupons() 
        if self.is_export_coupons:
            self.export_coupons()
        if self.is_update_coupon:
            self.update_coupons()
        if self.is_import_stock:
            self.import_stock() 
        if self.sync_attributes:
            self.sync_woo_attributes()                                 
        return True
    
    """Set only images in WooCommere Product"""
    @api.multi
    def set_product_images(self):
        woo_product_tmpl_obj=self.env['woo.product.template.ept']
        if self._context.get('process')=='set_product_images':
            woo_tmpl_ids=self._context.get('active_ids')
            instances=self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:
            woo_tmpl_ids=[]            
            instances=self.instance_ids            

        for instance in instances:
            if woo_tmpl_ids:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('id','in',woo_tmpl_ids),('exported_in_woo','=',True)])
            else:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])
            if instance.woo_version == 'old':
                woo_templates and woo_templates.set_old_products_images_in_woo(instance)
            elif instance.woo_version == 'new':                    
                woo_templates and woo_templates.set_new_products_images_in_woo(instance)
        return True    
    
    @api.multi
    def export_product_tags(self):
        product_tag_obj=self.env['woo.tags.ept']        
        instances=[]
        woo_tag_ids=[]
        if self._context.get('process')=='export_product_tags':
            woo_tag_ids=self._context.get('active_ids')
            instances = self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:                       
            instances=self.instance_ids
             
        for instance in instances:
            woo_product_tags=[]
            
            if woo_tag_ids:
                woo_product_tags=product_tag_obj.search([('woo_instance_id','=',instance.id),('id','in',woo_tag_ids),('exported_in_woo','=',False)])                
            else:
                woo_product_tags=product_tag_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',False)])                
                
            if woo_product_tags:
                product_tag_obj.export_product_tags(instance,woo_product_tags)
        return True   
   
    """This method is used to export coupons from odoo to woocommerce"""
    @api.multi
    def export_coupons(self):
        woo_coupons_obj=self.env['woo.coupons.ept']        
        instances=[]
        woo_coupons_code=[]
        if self._context.get('process')=='export_coupons':
            woo_coupons_code=self._context.get('active_ids')
            instances = self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:                       
            instances=self.instance_ids
             
        for instance in instances:
            woo_coupons=[]
            
            if woo_coupons_code:
                woo_coupons=woo_coupons_obj.search([('woo_instance_id','=',instance.id),('id','in',woo_coupons_code)])                
            else:
                woo_coupons=woo_coupons_obj.search([('woo_instance_id','=',instance.id)])                
                
            if woo_coupons:
                woo_coupons_obj.export_coupons(instance,woo_coupons)
                
        return True
    
    """This method is used to update coupons from odoo to woocommerce"""
    @api.multi
    def update_coupons(self):
        woo_coupons_obj=self.env['woo.coupons.ept']        
        instances=[]
        woo_coupons_code=[]
        if self._context.get('process')=='update_coupons':
            woo_coupons_code=self._context.get('active_ids')
            instances = self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:                       
            instances=self.instance_ids
             
        for instance in instances:
            woo_coupons=[]
            
            if woo_coupons_code:
                woo_coupons=woo_coupons_obj.search([('woo_instance_id','=',instance.id),('id','in',woo_coupons_code)])                
            else:
                woo_coupons=woo_coupons_obj.search([('woo_instance_id','=',instance.id)])                
                
            if woo_coupons:
                woo_coupons_obj.update_coupons(instance,woo_coupons)
                
        return True
   
    @api.multi
    def update_product_tags(self):
        product_tag_obj=self.env['woo.tags.ept']
        woo_tag_ids=[]
        instances=[]
        
        if self._context.get('process')=='update_product_tags':
            woo_tag_ids=self._context.get('active_ids')
            instances=self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:            
            instances=self.instance_ids
            
        for instance in instances:
            woo_product_tags=[]
            if woo_tag_ids:
                woo_product_tags=product_tag_obj.search([('woo_tag_id','!=',False),('woo_instance_id','=',instance.id),('id','in',woo_tag_ids),('exported_in_woo','=',True)])
            else:
                woo_product_tags=product_tag_obj.search([('woo_tag_id','!=',False),('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])

            if woo_product_tags:
                product_tag_obj.update_product_tags_in_woo(instance,woo_product_tags)
        return True    
    
    @api.multi
    def export_product_categ(self):
        product_categ_obj=self.env['woo.product.categ.ept']
        woo_categ_ids=[]
        woo_product_categs=[]
        instances=[]
        
        if self._context.get('process') == 'export_product_categ':
            woo_categ_ids=self._context.get('active_ids')
            instances = self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:
            instances=self.instance_ids                
                     
        for instance in instances:
            if woo_categ_ids:                      
                woo_product_categs=product_categ_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',False),('id','in',woo_categ_ids)])                
            else:
                woo_product_categs=product_categ_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',False)])
            if woo_product_categs:    
                product_categ_obj.export_product_categs(instance,woo_product_categs)
        return True
    
    @api.multi
    def update_product_categ(self):
        product_categ_obj=self.env['woo.product.categ.ept']        
        woo_categ_ids=[]
        woo_product_categs=[]
        instances=[]
        
        if self._context.get('process') == 'update_product_categ':
            woo_categ_ids=self._context.get('active_ids')
            instances = self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:
            instances=self.instance_ids            
            
        for instance in instances:
            if woo_categ_ids:
                woo_product_categs=product_categ_obj.search([('woo_categ_id','!=',False),('woo_instance_id','=',instance.id),('exported_in_woo','=',True),('id','in',woo_categ_ids)])
            else:
                woo_product_categs=product_categ_obj.search([('woo_categ_id','!=',False),('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])

            if woo_product_categs:
                product_categ_obj.update_product_categs_in_woo(instance,woo_product_categs)
        return True
    
    @api.multi
    def sync_woo_attributes(self):
        woo_template_obj=self.env['woo.product.template.ept']
        for instance in self.instance_ids:
            woo_template_obj.sync_woo_attribute(instance)

    @api.multi
    def sync_product_category(self):
        product_categ_obj=self.env['woo.product.categ.ept']
        for instance in self.instance_ids:            
            product_categ_obj.sync_product_category(instance)
        return True
    
    @api.multi
    def sync_product_tags(self):
        product_tags_obj=self.env['woo.tags.ept']
        for instance in self.instance_ids:            
            product_tags_obj.sync_product_tags(instance)
        return True         
    
    @api.multi
    def sync_coupons(self):
        coupons_obj=self.env['woo.coupons.ept']
        for instance in self.instance_ids:            
            coupons_obj.sync_coupons(instance)
        return True         
    
    @api.multi
    def import_sale_orders(self):
        sale_order_obj=self.env['sale.order']        
        for instance in self.instance_ids:
            if not instance.import_order_status_ids:
                raise Warning('Please select atleast one Order Status in Settings to import orders for Instance %s'%(instance.name))
            if instance.woo_version == 'old':
                before_date=self.past_orders_before_date
                after_date=self.past_orders_after_date
                sale_order_obj.import_woo_orders(instance,before_date,after_date,is_cron=False)
            elif instance.woo_version == 'new':
                before_date=self.past_orders_before_date
                after_date=self.past_orders_after_date
                sale_order_obj.import_new_woo_orders(instance,before_date,after_date,is_cron=False)
        return True
    
    @api.multi
    def import_woo_customers(self):
        res_partner_obj=self.env['res.partner']        
        for instance in self.instance_ids:        
            res_partner_obj.import_woo_customers(instance)
        return True    
    
    @api.multi
    def update_order_status(self):
        sale_order_obj=self.env['sale.order']
        for instance in self.instance_ids:
            sale_order_obj.update_woo_order_status(instance)
        return True            
    
    @api.multi
    def prepare_product_for_export(self):
        woo_template_obj=self.env['woo.product.template.ept']
        woo_product_obj=self.env['woo.product.product.ept']
        woo_product_categ=self.env['woo.product.categ.ept']
        woo_product_image_obj = self.env['woo.product.image.ept']
        template_ids=self._context.get('active_ids',[])
        odoo_templates=self.env['product.template'].search([('id','in',template_ids),('default_code','!=',False)])
        if not odoo_templates:
            raise Warning("Internel Reference (SKU) not set in selected products")
        for instance in self.instance_ids:
            for odoo_template in odoo_templates:
                woo_categ_ids = [(6, 0, [])]
                woo_template = woo_template_obj.search([('woo_instance_id','=',instance.id),('product_tmpl_id','=',odoo_template.id)])                
                if not woo_template:
                    categ_obj = odoo_template.categ_id or ''
                    if categ_obj.id:
                        self.create_categ_in_woo(categ_obj,instance) #create category
                        ctg = categ_obj.name.lower().replace('\'','\'\'')
                        self._cr.execute("select id from woo_product_categ_ept where LOWER(name) = '%s' and woo_instance_id = %s limit 1"%(ctg,instance.id))
                        woo_product_categ_id = self._cr.dictfetchall()
                        woo_categ_id = False
                        if woo_product_categ_id:
                            woo_categ_id = woo_product_categ.browse(woo_product_categ_id[0].get('id'))                        
                        if not woo_categ_id:             
                            woo_categ_id = woo_product_categ.create({'name':categ_obj.name,'woo_instance_id':instance.id})
                        else:
                            woo_categ_id.write({'name':categ_obj.name})
                        woo_categ_ids = [(6, 0, woo_categ_id.ids)]
                    woo_template=woo_template_obj.create({'woo_instance_id':instance.id,'product_tmpl_id':odoo_template.id,'name':odoo_template.name,'woo_categ_ids':woo_categ_ids,'description':odoo_template.description_sale,'short_description':odoo_template.description})
                    if odoo_template.image:
                        woo_product_image_obj.create({'sequence':0,'woo_instance_id':instance.id,'image':odoo_template.image,'woo_product_tmpl_id':woo_template.id})
                for variant in odoo_template.product_variant_ids:
                    woo_variant = woo_product_obj.search([('woo_instance_id','=',instance.id),('product_id','=',variant.id)])
                    if not woo_variant:
                        woo_variant.create({'woo_instance_id':instance.id,'product_id':variant.id,'woo_template_id':woo_template.id,'default_code':variant.default_code,'name':variant.display_name,'woo_variant_url':variant.image_url or ''})
        return True
    
    """ Create Category tree in woo commerce module """
    @api.multi
    def create_categ_in_woo(self,categ_id,instance,ctg_list = []):
        woo_product_categ=self.env['woo.product.categ.ept']
        if categ_id:
            ctg_list.append(categ_id)
            self.create_categ_in_woo(categ_id.parent_id,instance,ctg_list=ctg_list)
        else:
            for categ_id in list(OrderedDict.fromkeys(reversed(ctg_list))):
                woo_product_parent_categ = categ_id.parent_id and woo_product_categ.search([('name','=',categ_id.parent_id.name),('woo_instance_id','=',instance.id)],limit=1) or False
                if woo_product_parent_categ:
                    woo_product_category = woo_product_categ.search([('name','=',categ_id.name),('parent_id','=',woo_product_parent_categ.id),('woo_instance_id','=',instance.id)],limit=1)
                else:
                    woo_product_category = woo_product_categ.search([('name','=',categ_id.name),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_product_category:
                    if not categ_id.parent_id:
                        parent_id = woo_product_categ.create({'name':categ_id.name,'woo_instance_id':instance.id})
                    else:
                        parent_id = woo_product_categ.search([('name','=',categ_id.parent_id.name),('woo_instance_id','=',instance.id)],limit=1)
                        woo_product_categ.create({'name':categ_id.name,'woo_instance_id':instance.id,'parent_id':parent_id.id})
                elif not woo_product_category.parent_id and categ_id.parent_id:
                    parent_id = woo_product_categ.search([('name','=',categ_id.parent_id.name),('parent_id','=',woo_product_parent_categ.id),('woo_instance_id','=',instance.id)])
                    if not parent_id:
                        woo_product_categ.create({'name':categ_id.name,'woo_instance_id':instance.id})
                    if not parent_id.parent_id.id==woo_product_category.id and woo_product_categ.instance_id.id==instance.id:
                        woo_product_category.write({'parent_id':parent_id.id})
        return True
    
    @api.multi
    def publish_multiple_products(self):
        woo_template_obj=self.env['woo.product.template.ept']
        if self._context.get('process')=='publish_multiple_products':
            woo_template_ids=self._context.get('active_ids',[])
            woo_templates=woo_template_obj.search([('id','in',woo_template_ids),('exported_in_woo','=',True),('website_published','=',False)])
        else:
            woo_templates=woo_template_obj.search([('exported_in_woo','=',True),('website_published','=',False)])
        for woo_template in woo_templates:
            woo_template.woo_published()
        return True
    
    @api.multi
    def unpublish_multiple_products(self):
        woo_template_obj=self.env['woo.product.template.ept']
        if self._context.get('process')=='unpublish_multiple_products':
            woo_template_ids=self._context.get('active_ids',[])
            woo_templates=woo_template_obj.search([('id','in',woo_template_ids),('exported_in_woo','=',True),('website_published','=',True)])
        else:
            woo_templates=woo_template_obj.search([('exported_in_woo','=',True),('website_published','=',True)])
        for woo_template in woo_templates:
            woo_template.woo_unpublished()
        return True    
    
    @api.multi
    def update_products(self):
        woo_product_tmpl_obj=self.env['woo.product.template.ept']
        if self._context.get('process')=='update_products':
            woo_tmpl_ids=self._context.get('active_ids')
            instances=self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:
            woo_tmpl_ids=[]            
            instances=self.instance_ids            

        for instance in instances:
            if woo_tmpl_ids:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('id','in',woo_tmpl_ids),('exported_in_woo','=',True)])
            else:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])
            if instance.woo_version == 'old' and woo_templates:
                woo_product_tmpl_obj.update_products_in_woo(instance,woo_templates,self.update_image_in_product_update)
            elif instance.woo_version == 'new' and woo_templates:
                woo_product_tmpl_obj.update_new_products_in_woo(instance,woo_templates,self.update_image_in_product_update)
        return True    
    
    @api.multi
    def update_stock_in_woo(self):
        woo_product_tmpl_obj=self.env['woo.product.template.ept']
        if self._context.get('process')=='update_stock':
            woo_tmpl_ids=self._context.get('active_ids')
            instances=self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:            
            woo_tmpl_ids=[]
            instances=self.instance_ids
        
        for instance in instances:
            if woo_tmpl_ids:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('id','in',woo_tmpl_ids)])
            else:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])
            if instance.woo_version == 'old' and woo_templates:    
                woo_product_tmpl_obj.update_stock_in_woo(instance,woo_templates)
            elif instance.woo_version == 'new' and woo_templates:
                woo_product_tmpl_obj.update_new_stock_in_woo(instance,woo_templates)
        return True    
    
    @api.multi
    def update_price(self):
        woo_product_tmpl_obj=self.env['woo.product.template.ept']
        if self._context.get('process')=='update_price':
            woo_product_tmpl_ids=self._context.get('active_ids')
            instances=self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:            
            woo_product_tmpl_ids=[]
            instances=self.instance_ids

        for instance in instances:
            if woo_product_tmpl_ids:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True),('id','in',woo_product_tmpl_ids)])
            else:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',True)])
            if instance.woo_version == 'old' and woo_templates:
                woo_product_tmpl_obj.update_price_in_woo(instance,woo_templates)
            elif instance.woo_version == 'new' and woo_templates:
                woo_product_tmpl_obj.update_new_price_in_woo(instance,woo_templates)
        return True    

    @api.multi
    def check_products(self,woo_templates):
        if self.env['woo.product.product.ept'].search([('woo_template_id','in',woo_templates.ids),('default_code','=',False)]):
            raise Warning("Default code is not set in some variants")
    
    @api.multi
    def filter_templates(self,woo_templates):
        filter_templates=[]
        for woo_template in woo_templates:
            if not self.env['woo.product.product.ept'].search([('woo_template_id','=',woo_template.id),('default_code','=',False)]):
                filter_templates.append(woo_template)
        return filter_templates    
    
    @api.multi
    def export_products(self):
        instance_settings = {}
        config_settings = {}
        
        is_set_price = False
        is_set_stock = False
        is_set_image = False
        is_publish = False
        
        woo_product_tmpl_obj=self.env['woo.product.template.ept']
        if self._context.get('process')=='export_products':
            woo_template_ids=self._context.get('active_ids')
            instances = self.env['woo.instance.ept'].search([('state','=','confirmed')])
        else:            
            woo_template_ids=[]
            instances=self.instance_ids
            for instance in instances:
                instance_settings.update({"instance_id":instance})
                if instance.is_set_price:
                    config_settings.update({"is_set_price":True})
                if instance.is_set_stock:
                    config_settings.update({"is_set_stock":True})
                if instance.is_set_image:
                    config_settings.update({"is_set_image":True})
                if instance.is_publish:
                    config_settings.update({"is_publish":True})
                instance_settings.update({"settings":config_settings})        
        
        for instance in instances:
            if instance_settings:
                setting = instance_settings.get('settings')
                is_set_price = setting.get('is_set_price')
                is_set_stock = setting.get('is_set_stock')
                is_set_image = setting.get('is_set_image')
                is_publish = setting.get('is_publish')
            else:
                is_set_price = self.update_price_in_product
                is_set_stock = self.update_stock_in_product
                is_set_image = self.update_image_in_product_export
                is_publish = self.publish
                                
            if woo_template_ids:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('id','in',woo_template_ids)])
                woo_templates=self.filter_templates(woo_templates)
            else:
                woo_templates=woo_product_tmpl_obj.search([('woo_instance_id','=',instance.id),('exported_in_woo','=',False)])
                self.check_products(woo_templates)
            if instance.woo_version == 'old' and woo_templates:
                woo_product_tmpl_obj.export_products_in_woo(instance,woo_templates,is_set_price,is_set_stock,is_publish,is_set_image)
            elif instance.woo_version == 'new' and woo_templates:
                woo_product_tmpl_obj.export_new_products_in_woo(instance,woo_templates,is_set_price,is_set_stock,is_publish,is_set_image)
        return True
    
    @api.multi
    def sync_selective_products(self):
        active_ids=self._context.get('active_ids')
        woo_template_obj=self.env['woo.product.template.ept']        
        woo_templates=woo_template_obj.search([('id','in',active_ids),('woo_tmpl_id','=',False)])
        if woo_templates:
            raise Warning("You can only sync already exported products")
        woo_templates=woo_template_obj.search([('id','in',active_ids)])
        for woo_template in woo_templates:
            if woo_template.woo_instance_id.woo_version == 'old':
                woo_template_obj.sync_products(woo_template.woo_instance_id,woo_tmpl_id=woo_template.woo_tmpl_id,update_price=self.sync_price_with_product,sync_images_with_product=self.sync_images_with_product)
            elif woo_template.woo_instance_id.woo_version == 'new':
                woo_template_obj.sync_new_products(woo_template.woo_instance_id,woo_tmpl_id=woo_template.woo_tmpl_id,update_price=self.sync_price_with_product,sync_images_with_product=self.sync_images_with_product)
        return True
    
    @api.multi
    def sync_products(self):
        woo_template_obj=self.env['woo.product.template.ept']
        skip_existing_products = self.is_skip_sync_existing_product
        for instance in self.instance_ids:
            if instance.woo_version == 'old':
                woo_template_obj.sync_products(instance,update_price=instance.sync_price_with_product,sync_images_with_product=instance.sync_images_with_product, skip_existing_products=skip_existing_products)
            elif instance.woo_version == 'new':
                woo_template_obj.sync_new_products(instance,update_price=instance.sync_price_with_product,sync_images_with_product=instance.sync_images_with_product, skip_existing_products=skip_existing_products)
        return True
    
    @api.multi
    def import_stock(self):
        transaction_log_obj=self.env['woo.transaction.log']
        stock_inventory_line_obj = self.env["stock.inventory.line"]
        for instance in self.instance_ids:
            wcapi=instance.connect_in_woo()
            prodcuts_stock=[]
            if instance.is_latest:
                products=self.env['woo.product.product.ept'].search([('variant_id','!=',False),('exported_in_woo','=',True),('woo_instance_id','=',instance.id)])
                for product in products:
                    if product.woo_template_id.woo_tmpl_id==product.variant_id:
                        try:
                            res=wcapi.get("products/%s"%(product.variant_id))
                            stock_data={}
                            if res.status_code not in ['201','200']:
                                if res.json().get('manage_stock'):
                                    if product.product_id.type=='product':
                                        product_qty=res.json().get('stock_quantity')
                                        stock_data.update({'product_qty':product_qty})
                                        stock_data.update({'product_id':product.product_id})
                                        prodcuts_stock.append(stock_data)
                            else:
                                transaction_log_obj.create({'message':'Import Stock for product %s has not proper response.\n Response %s'%(product.name,res.content),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                        except Exception as e:
                            transaction_log_obj.create({'message':'Import Stock for product %s not perfom.\n Error %s'%(product.name,e),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                    else:
                        try:
                            res=wcapi.get("products/%s/variations/%s"%(product.woo_template_id.woo_tmpl_id,product.variant_id))
                            stock_data={}
                            if res.status_code not in ['201','200']:
                                if res.json().get('manage_stock'):
                                    if product.product_id.type=='product':
                                        product_qty=res.json().get('stock_quantity')
                                        stock_data.update({'product_qty':product_qty})
                                        stock_data.update({'product_id':product.product_id})
                                        prodcuts_stock.append(stock_data)
                            else:
                                transaction_log_obj.create({'message':'Import Stock for product %s has not proper response.\n Response %s'%(product.name,res.content),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
                        except Exception as e:
                            transaction_log_obj.create({'message':'Import Stock for product %s not perform.\n Error %s'%(product.name,e),
                                             'mismatch_details':True,
                                             'type':'product',
                                             'woo_instance_id':instance.id
                                            })
            else:
                product_templates=self.env['woo.product.template.ept'].search([('exported_in_woo','=',True),('woo_instance_id','=',instance.id)])
                for product_template in product_templates:
                    try:
                        res=wcapi.get("products/%s"%(product_template.woo_tmpl_id))
                        if res.status_code not in ['201','200']:
                            response=res.json()
                            if instance.woo_version=='old':
                                response=response.get('product')
                            if response.get('type')=='simple':
                                stock_data={}
                                manage_stock=response.get('managing_stock') if instance.woo_version=='old' else response.get('manage_stock')
                                if manage_stock and product_template.product_tmpl_id.product_variant_ids.type=='product':
                                    product_qty=response.get('stock_quantity')
                                    stock_data.update({'product_qty':product_qty})
                                    stock_data.update({'product_id':product_template.product_tmpl_id.product_variant_ids})
                                    prodcuts_stock.append(stock_data)
                            else:
                                for variation in response.get('variations'):
                                    for product in product_template.product_tmpl_id.product_variant_ids:
                                        if variation.get('sku')==product.default_code and product.type=='product': 
                                            if variation.get('managing_stock') or variation.get('manage_stock'):
                                                stock_data={}
                                                product_qty=variation.get('stock_quantity')
                                                stock_data.update({'product_qty':product_qty})
                                                stock_data.update({'product_id':product})
                                                prodcuts_stock.append(stock_data)
                        else:
                            transaction_log_obj.create({'message':'Import Stock for product %s has not proper response.\n Response %s'%(product_template.name,res.content),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
                    except Exception as e:
                        transaction_log_obj.create({'message':'Import Stock for product %s not perform.\n Error %s'%(product_template.name,e),
                                         'mismatch_details':True,
                                         'type':'product',
                                         'woo_instance_id':instance.id
                                        })
            if prodcuts_stock:
                self.env['stock.inventory'].create_stock_inventory(prodcuts_stock,instance.warehouse_id.lot_stock_id,auto_validate=False)
                # invetory_id=self.env['stock.inventory'].create({'name':'Inventory For Instance %s'%(instance.name),'location_id':instance.warehouse_id.lot_stock_id.id,'filter':'partial'})
                # for product_stock in prodcuts_stock:
                #     stock_inventory_line = stock_inventory_line_obj.create({"inventory_id":invetory_id.id,"product_id":product_stock.get('product_id'),"location_id":invetory_id.location_id.id,"product_qty":product_stock.get('stock_qty')})
                #     stock_inventory_line._onchange_product()
                # if invetory_id:
                #     instance.write({'inventory_adjustment_id':invetory_id.id})
        return True
                
