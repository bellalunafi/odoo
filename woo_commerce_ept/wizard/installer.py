import logging
import requests
from .. import woocommerce
from odoo.exceptions import Warning
_logger = logging.getLogger(__name__)

from odoo import models,fields,api,_

from datetime import datetime
from dateutil.relativedelta import relativedelta

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

class woo_instance_config_installer(models.TransientModel):
    _name = 'woo.instance.config.installer'
    _inherit = 'res.config.installer'

    name = fields.Char("Instance Name")
    consumer_key=fields.Char("Consumer Key",required=True,help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> API >> Keys/Apps >> Click on Add Key")
    consumer_secret=fields.Char("Consumer Secret",required=True,help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> API >> Keys/Apps >> Click on Add Key")    
    host=fields.Char("Host",required=True)
    verify_ssl=fields.Boolean("Verify SSL",default=False,help="Check this if your WooCommerce site is using SSL certificate")
    country_id = fields.Many2one('res.country',string = "Country",required=True)
    is_image_url = fields.Boolean("Is Image URL?",help="Check this if you use Images from URL\nKepp as it is if you use Product images")
    admin_username=fields.Char("Username", help="WooCommerce UserName,Used to Export Image Files.")
    admin_password=fields.Char("Password", help="WooCommerce Password,Used to Export Image Files.")
    woo_version = fields.Selection([('new','2.6+'),('old','<=2.6')],default='old',string="WooCommerce Version",help="Set the appropriate WooCommerce Version you are using currently or\nLogin into WooCommerce site,Go to Admin Panel >> Plugins")    
    is_latest=fields.Boolean('3.0 or later',default=False)
    
    @api.multi
    def modules_to_install(self):
        modules = super(woo_instance_config_installer, self).modules_to_install()
        return set([])
    
    @api.multi
    def execute(self):
        host = self.host
        consumer_key = self.consumer_key
        consumer_secret = self.consumer_secret
        wp_api = True if self.woo_version == 'new' else False
        version = "wc/v1" if wp_api else "v3"
        if self.is_latest:
            version = "wc/v2"
        wcapi = woocommerce.api.API(url=host, consumer_key=consumer_key,
                    consumer_secret=consumer_secret,verify_ssl=self.verify_ssl,wp_api=wp_api,version=version,query_string_auth=True)        
        r = wcapi.get("products")
        if not isinstance(r,requests.models.Response):
            raise Warning(_("Response is not in proper format :: %s"%(r)))
        if r.status_code != 200:
            raise Warning(_("%s\n%s"%(r.status_code,r.reason)))        
        else:    
            instance=self.env['woo.instance.ept'].create({'name':self.name,
                                                 'consumer_key':self.consumer_key,                                                 
                                                 'consumer_secret':self.consumer_secret,                                                 
                                                 'host':self.host,
                                                 'verify_ssl':self.verify_ssl,
                                                 'country_id':self.country_id.id,
                                                 'company_id':self.env.user.company_id.id,
                                                 'is_image_url':self.is_image_url,
                                                 'woo_version':self.woo_version,
                                                 'is_latest':self.is_latest,
                                                 'admin_username':self.admin_username,
                                                 'admin_password':self.admin_password                                                                                                                                                
                                                 })
            if instance.is_latest:
                self.env['woo.payment.gateway'].get_payment_gateway(instance)
        return super(woo_instance_config_installer, self).execute()
    
class sale_workflow_process_config_installer(models.TransientModel):
    _name = 'sale.workflow.process.config.installer'
    _inherit = 'res.config.installer'
    
    @api.model
    def default_get(self,fields):
        result = super(sale_workflow_process_config_installer,self).default_get(fields)
        workflow= self.env['sale.workflow.process.ept'].search([],limit=1)
        workflow and result.update({'name':workflow.name,
                                    'validate_order':workflow.validate_order,
                                    'create_invoice':workflow.create_invoice,
                                    'validate_invoice':workflow.validate_invoice,
                                    'register_payment':workflow.register_payment,
                                    'invoice_date_is_order_date':workflow.invoice_date_is_order_date,
                                    'journal_id':workflow.journal_id.id,
                                    'sale_journal_id':workflow.sale_journal_id.id,
                                    'picking_policy':workflow.picking_policy,
                                    'auto_check_availability':workflow.auto_check_availability,
                                    'invoice_policy':workflow.invoice_policy})        
        return result
    
    @api.multi
    def modules_to_install(self):
        modules = super(sale_workflow_process_config_installer, self).modules_to_install()
        return set([])
    
    @api.model
    def _default_journal(self):
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', list(filter(None, map(TYPE2JOURNAL.get, inv_types)))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)
        
    name = fields.Char(string='Name', size=64)
    validate_order = fields.Boolean("Validate Order",default=False,help="Directly Confirm Sale and create Sales Order when importing an order.")
    create_invoice = fields.Boolean('Create Invoice',default=False,help="Create Invoice of the Sales Order that is imported.")
    validate_invoice = fields.Boolean(string='Validate Invoice',default=False,help="Automatically validate invoice of the Sales Order that is imported.")
    register_payment=fields.Boolean(string='Register Payment',default=False,help="Automatically Register Payment of the Sales Order that is imported.")
    invoice_date_is_order_date = fields.Boolean('Force Invoice Date', help="Keep Invoice date same as Order date.")
    journal_id = fields.Many2one('account.journal', string='Payment Journal',domain=[('type','in',['cash','bank'])],help="Select a journal where you want to create supplier invoice entries.")
    sale_journal_id = fields.Many2one('account.journal', string='Sales Journal',default=_default_journal,domain=[('type','=','sale')],help="Select a journal where you want to create customer invoice entries.")
    picking_policy =  fields.Selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')], string='Shipping Policy',help="Choose if you want to ship all products at once or each product when they are available.")
    auto_check_availability=fields.Boolean("Auto Check Availability",default=False)
    invoice_policy = fields.Selection([('order', 'Ordered quantities'),('delivery', 'Delivered quantities'),],string='Invoicing Policy',help="Choose if you want to create invoice based on ordered quantities or delivered quantities.")
    
    @api.onchange("validate_order")
    def onchange_invoice_on(self):
        for record in self:
            if not record.validate_order:
                record.auto_check_availability=False    
    
    @api.multi
    def execute(self):
        workflow= self.env['sale.workflow.process.ept'].search([],limit=1)
        workflow and workflow.write({'name':self.name,
                                    'validate_order':self.validate_order,
                                    'create_invoice':self.create_invoice,
                                    'validate_invoice':self.validate_invoice,
                                    'register_payment':self.register_payment,
                                    'invoice_date_is_order_date':self.invoice_date_is_order_date,
                                    'journal_id':self.journal_id.id,
                                    'sale_journal_id':self.sale_journal_id.id,
                                    'picking_policy':self.picking_policy,
                                    'auto_check_availability':self.auto_check_availability,
                                    'invoice_policy':self.invoice_policy})
        return super(sale_workflow_process_config_installer, self).execute()
    
class woo_instance_financial_status_config_installer(models.TransientModel):
    _name = 'woo.instance.financial.status.config.installer'
    _inherit = 'res.config.installer'
    
    financial_status=fields.Selection([('paid','The finances have been paid'),
                                        ('not_paid','The finances have been not paid'),                                        
                                        ],default="paid",required=1)
    auto_workflow_id=fields.Many2one("sale.workflow.process.ept","Auto Workflow",required=1)
    payment_gateway_id=fields.Many2one("woo.payment.gateway","Payment Gateway",required=1,help="The payment code should match Gateway ID in your WooCommerce Checkout Settings.")
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",required=1)    
    
    @api.multi
    def modules_to_install(self):
        modules = super(woo_instance_financial_status_config_installer, self).modules_to_install()
        return set([])

    @api.multi
    def execute(self):
        self.env['woo.sale.auto.workflow.configuration'].create({'woo_instance_id':self.woo_instance_id.id,
                                                 'auto_workflow_id':self.auto_workflow_id.id,
                                                 'payment_gateway_id':self.payment_gateway_id.id,                                                 
                                                 'financial_status':self.financial_status                                                                                                                                                                                                                                                
                                                 })
        return super(woo_instance_financial_status_config_installer, self).execute()            
    
class woo_instance_general_config_installer(models.TransientModel):
    _name = 'woo.instance.general.config.installer'
    _inherit = 'res.config.installer'
    
    @api.multi
    def modules_to_install(self):
        modules = super(woo_instance_general_config_installer, self).modules_to_install()
        return set([])    
        
    @api.model
    def _default_instance(self):
        instances = self.env['woo.instance.ept'].search([])
        return instances and instances[0].id or False
    
   
    @api.model
    def _get_default_company(self):
        company_id = self.env.user._get_company()
        if not company_id:
            raise Warning(_('There is no default company for the current user!'))
        return company_id
        
    woo_instance_id = fields.Many2one('woo.instance.ept', 'Instance', default=_default_instance,help="Select WooCommerce Instance that you want to configure.")
    warehouse_id = fields.Many2one('stock.warehouse',string = "Warehouse",help="Stock Management, Order Processing & Fulfillment will be carried out from this warehouse.")
    company_id = fields.Many2one('res.company',string='Company',help="Orders and Invoices will be generated of this company.")
    country_id = fields.Many2one('res.country',string = "Country")
    lang_id = fields.Many2one('res.lang', string='Language',help="Select language for WooCommerce customer.")
    order_prefix = fields.Char(size=10, string='Order Prefix')
    import_order_status_ids = fields.Many2many('import.order.status','woo_installer_order_status_rel','installer_id','status_id',"Import Order Status",help="Selected status orders will be imported from WooCommerce")          

    stock_field = fields.Many2one('ir.model.fields', string='Stock Field',help="Choose if you want to update stock to WooCommerce based on Quantity on Hand or Forecasted Quantity (Onhand - Outgoing).")
    
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',help="Product Price will be calculated in Odoo based on this pricelist.")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term',help="Select the condition of payment for invoice.")    
    section_id=fields.Many2one('crm.team', 'Sales Team',help="Choose Sales Team that handles the order you import.")
        
    
    discount_product_id=fields.Many2one("product.product","Discount",domain=[('type','=','service')],required=False,help="Discount provided via coupon codes for promotional offers.")
    fee_line_id=fields.Many2one("product.product","Fees",domain=[('type','=','service')],required=False,help="Any Extra fees applicable under specific condition(s) (e.g., Extra $20 if payment method is COD).")

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')                              
    
    auto_import_product = fields.Boolean(string="Auto Create Product if not found?",help="Check if you want to automatically import orders at certain interval.")   
    order_auto_import = fields.Boolean(string='Auto Order Import?')
    order_import_interval_number = fields.Integer('Import Order Interval Number',help="Repeat every x.")
    order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Import Order Interval Unit')
    order_import_next_execution = fields.Datetime('Next Execution Time For Order Import', help='Next execution time')
    order_import_user_id = fields.Many2one('res.users',string="User",help='User',default=lambda self: self.env.user)
    
    
    order_auto_update=fields.Boolean(string="Auto Order Update ?",help="Check if you want to automatically update order status to WooCommerce.")
    order_update_interval_number = fields.Integer('Update Order Interval Number',help="Repeat every x.")
    order_update_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Order Interval Unit')               
    order_update_next_execution = fields.Datetime('Next Execution Time For Order Update', help='Next execution time')
    order_update_user_id = fields.Many2one('res.users',string="Order Update User",help='Order Update User',default=lambda self: self.env.user)
    
    stock_auto_export=fields.Boolean('Stock Auto Update.', default=False,help="Check if you want to automatically update stock levels from Odoo to WooCommerce.")
    update_stock_interval_number = fields.Integer('Update Order Interval Number Time',help="Repeat every x.")
    update_stock_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Update Order Interval Unit Time')
    update_stock_next_execution = fields.Datetime('Next Execution Time for Stock Update', help='Update Stock Next execution time')
    update_stock_user_id = fields.Many2one('res.users',string="Update Stock User",help='User',default=lambda self: self.env.user)
    
    is_set_price = fields.Boolean(string="Set Price ?",default=False)
    is_set_stock = fields.Boolean(string="Set Stock ?",default=False)
    is_publish = fields.Boolean(string="Publish In Website ?",default=False)
    is_set_image = fields.Boolean(string="Set Image ?",default=False)    
    sync_images_with_product=fields.Boolean("Sync/Import Images?",help="Check if you want to import images along with products",default=False)
    sync_price_with_product=fields.Boolean("Sync/Import Product Price?",help="Check if you want to import price along with products",default=False)
    
    @api.onchange('woo_instance_id')
    def onchange_instance_id(self):        
        instance = self.woo_instance_id or False
        self.company_id=instance and instance.company_id and instance.company_id.id or False
        self.warehouse_id = instance and instance.warehouse_id and instance.warehouse_id.id or False
        self.country_id = instance and instance.country_id and instance.country_id.id or False
        self.lang_id = instance and instance.lang_id and instance.lang_id.id or False
        self.order_prefix = instance and instance.order_prefix or ''
        self.import_order_status_ids = instance and instance.import_order_status_ids.ids
        self.stock_field = instance and instance.stock_field and instance.stock_field.id or False
        self.pricelist_id = instance and instance.pricelist_id and instance.pricelist_id.id or False
        self.payment_term_id = instance and instance.payment_term_id and instance.payment_term_id.id or False 
        self.fiscal_position_id = instance and instance.fiscal_position_id and instance.fiscal_position_id.id or False
        self.discount_product_id=instance and instance.discount_product_id and instance.discount_product_id.id or False
        self.fee_line_id=instance and instance.fee_line_id and instance.fee_line_id.id or False        
        self.order_auto_import=instance and instance.order_auto_import
        self.stock_auto_export=instance and instance.stock_auto_export        
        self.order_auto_update=instance and instance.order_auto_update
        self.auto_import_product=instance and instance.auto_import_product
        self.section_id=instance and instance.section_id and instance.section_id.id or False
        self.is_set_price = instance and instance.is_set_price or False
        self.is_set_stock = instance and instance.is_set_stock or False
        self.is_publish = instance and instance.is_publish or False
        self.is_set_image = instance and instance.is_set_image or False
        self.sync_images_with_product = instance and instance.sync_images_with_product or False
        self.sync_price_with_product = instance and instance.sync_price_with_product or False
        try:
            inventory_cron_exist = instance and self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            inventory_cron_exist=False
        if inventory_cron_exist:
            self.update_stock_interval_number=inventory_cron_exist.interval_number or False
            self.update_stock_interval_type=inventory_cron_exist.interval_type or False
             
        try:
            order_import_cron_exist = instance and self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            order_import_cron_exist=False
        if order_import_cron_exist:
            self.order_import_interval_number = order_import_cron_exist.interval_number or False
            self.order_import_interval_type = order_import_cron_exist.interval_type or False
        try:
            order_update_cron_exist = instance and self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status_instance_%d'%(instance.id),raise_if_not_found=False)
        except:
            order_update_cron_exist=False
        if order_update_cron_exist:
            self.order_update_interval_number= order_update_cron_exist.interval_number or False
            self.order_update_interval_type= order_update_cron_exist.interval_type or False

    @api.multi
    def execute(self):
        instance = self.woo_instance_id
        values = {}
        res = super(woo_instance_general_config_installer,self).execute()
        if instance:
            values['company_id'] = self.company_id and self.company_id.id or False
            values['warehouse_id'] = self.warehouse_id and self.warehouse_id.id or False
            values['country_id'] = self.country_id and self.country_id.id or False
            values['lang_id'] = self.lang_id and self.lang_id.id or False
            values['order_prefix'] = self.order_prefix and self.order_prefix
            values['import_order_status_ids'] = [(6,0,self.import_order_status_ids.ids)]           
            values['stock_field'] = self.stock_field and self.stock_field.id or False
            values['pricelist_id'] = self.pricelist_id and self.pricelist_id.id or False
            values['payment_term_id'] = self.payment_term_id and self.payment_term_id.id or False 
            values['fiscal_position_id'] = self.fiscal_position_id and self.fiscal_position_id.id or False
            values['discount_product_id']=self.discount_product_id.id or False 
            values['fee_line_id']=self.fee_line_id.id or False           
            values['order_auto_import']=self.order_auto_import
            values['stock_auto_export']=self.stock_auto_export            
            values['order_auto_update']=self.order_auto_update
            values['auto_import_product']=self.auto_import_product
            values['section_id']=self.section_id and self.section_id.id or False
            values['is_set_price']=self.is_set_price or False
            values['is_set_stock']=self.is_set_stock or False
            values['is_publish']=self.is_publish or False
            values['is_set_image']=self.is_set_image or False
            values['sync_images_with_product']=self.sync_images_with_product or False
            values['sync_price_with_product']=self.sync_price_with_product or False
            instance.write(values)
            instance.confirm()
            self.setup_order_import_cron(instance)
            self.setup_order_status_update_cron(instance)                             
            self.setup_update_stock_cron(instance)                 

        return res

    @api.multi   
    def setup_order_import_cron(self,instance):
        if self.order_auto_import:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.order_import_interval_type](self.order_import_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.order_import_interval_number,
                    'interval_type':self.order_import_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'args':"([{'woo_instance_id':%d}])"%(instance.id),
                    'user_id': self.order_import_user_id and self.order_import_user_id.id}
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of WooCommerce are deleted, please upgrade WooCommerce Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'woo_commerce_ept',
                                                  'name':'ir_cron_import_woo_orders_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_import_woo_orders_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True        
    
    @api.multi   
    def setup_order_status_update_cron(self,instance):
        if self.order_auto_update:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.order_update_interval_type](self.order_update_interval_number)
            vals = {'active' : True,
                    'interval_number':self.order_update_interval_number,
                    'interval_type':self.order_update_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'args':"([{'woo_instance_id':%d}])"%(instance.id),
                    'user_id': self.order_update_user_id and self.order_update_user_id.id
                    }
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    update_order_cron = self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status')
                except:
                    update_order_cron=False
                if not update_order_cron:
                    raise Warning('Core settings of WooCommerce are deleted, please upgrade WooCommerce Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_order_cron.name
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'woo_commerce_ept',
                                                  'name':'ir_cron_update_woo_order_status_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_update_stock_cron(self,instance):
        if self.stock_auto_export:
            try:                
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.update_stock_interval_type](self.update_stock_interval_number)
            vals = {'active' : True,
                    'interval_number':self.update_stock_interval_number,
                    'interval_type':self.update_stock_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'args':"([{'woo_instance_id':%d}])"%(instance.id),
                    'user_id': self.update_stock_user_id and self.update_stock_user_id.id}
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:                    
                    update_stock_cron = self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock')
                except:
                    update_stock_cron=False
                if not update_stock_cron:
                    raise Warning('Core settings of WooCommerce are deleted, please upgrade WooCommerce Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_stock_cron.name
                vals.update({'name':name})
                new_cron = update_stock_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'woo_commerce_ept',
                                                  'name':'ir_cron_update_woo_stock_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('woo_commerce_ept.ir_cron_update_woo_stock_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})        
        return True        