from odoo import models,fields,api,_
from odoo.exceptions import Warning
from .. import woocommerce
import requests

class woo_instance_ept(models.Model):
    _name="woo.instance.ept"
    _description = "WooCommerce Instance"

    @api.model
    def _default_stock_field(self):
        stock_field = self.env['ir.model.fields'].search(
            [('model_id.model', '=', 'product.product'), ('name', '=', 'virtual_available')], limit=1)
        return stock_field and stock_field.id or False

    @api.model
    def _default_payment_term(self):
        payment_term = self.env.ref("account.account_payment_term_immediate")
        return payment_term and payment_term.id or False

    @api.model
    def _default_order_status(self):
        order_status = self.env.ref('woo_commerce_ept.processing')
        return order_status and [(6, 0, [order_status.id])] or False

    @api.model
    def _default_discount_product(self):
        discount_product = self.env.ref('woo_commerce_ept.product_woo_discount_ept')
        return discount_product or False

    @api.model
    def _default_fee_product(self):
        fee_product = self.env.ref('woo_commerce_ept.product_woo_shipping_fees_ept')
        return fee_product or False

    @api.model
    def _get_default_warehouse(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1,
                                                       order='id')
        return warehouse and warehouse.id or False

    @api.model
    def _get_default_language(self):
        lang_code = self.env.user.lang
        language = self.env["res.lang"].search([('code', '=', lang_code)])
        return language and language.id or False
    
    name = fields.Char(size=120, string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', default=_get_default_warehouse)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    lang_id = fields.Many2one('res.lang', string='Language', default=_get_default_language)
    # Added by jigneshb
    use_custom_order_prefix = fields.Boolean(string="Use Custom Order Prefix",
                                             help="True:Use Custom Order Prefix, False:Default Sale Order Prefix")
    order_prefix = fields.Char(size=10, string='Order Prefix')
    import_order_status_ids = fields.Many2many('import.order.status', 'woo_instance_order_status_rel', 'instance_id',
                                               'status_id', "Import Order Status", default=_default_order_status,
                                               help="Selected status orders will be imported from WooCommerce")
    order_auto_import = fields.Boolean(string='Woo Auto Order Import?')
    order_auto_update=fields.Boolean(string="Woo Auto Order Update?")
    stock_auto_export=fields.Boolean(string="Woo Stock Auto Export?")
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    stock_field = fields.Many2one('ir.model.fields', string='Stock Field', default=_default_stock_field)
    country_id=fields.Many2one("res.country","Country")
    host=fields.Char("Host",required=True)
    auto_import_product = fields.Boolean(string="Auto Create Product if not found?", default=False)
    consumer_key=fields.Char("Consumer Key",required=True,help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> API >> Keys/Apps >> Click on Add Key")
    consumer_secret=fields.Char("Consumer Secret",required=True,help="Login into WooCommerce site,Go to Admin Panel >> WooCommerce >> Settings >> API >> Keys/Apps >> Click on Add Key")
    verify_ssl=fields.Boolean("Verify SSL",default=False,help="Check this if your WooCommerce site is using SSL certificate")      
    section_id=fields.Many2one('crm.team', 'Sales Team')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', default=_default_payment_term)
    discount_product_id = fields.Many2one("product.product", "Discount", domain=[('type', '=', 'service')],
                                          default=_default_discount_product)
    fee_line_id = fields.Many2one("product.product", "Fees", domain=[('type', '=', 'service')],
                                  default=_default_fee_product)
    last_inventory_update_time=fields.Datetime("Last Inventory Update Time")    
    state=fields.Selection([('not_confirmed','Not Confirmed'),('confirmed','Confirmed')],default='not_confirmed')
    is_image_url = fields.Boolean("Is Image URL?",help="Check this if you use Images from URL\nKepp as it is if you use Product images")
    admin_username=fields.Char("Username", help="WooCommerce UserName,Used to Export Image Files.")
    admin_password=fields.Char("Password", help="WooCommerce Password,Used to Export Image Files.")
    woo_version = fields.Selection([('new','2.6+'),('old','<=2.6')],default='old',string="WooCommerce Version",help="Set the appropriate WooCommerce Version you are using currently or\nLogin into WooCommerce site,Go to Admin Panel >> Plugins")
    is_latest=fields.Boolean('3.0 or later',default=False)
    is_set_price = fields.Boolean(string="Set Price ?", default=True)
    is_set_stock = fields.Boolean(string="Set Stock ?", default=True)
    is_publish = fields.Boolean(string="Publish In Website ?",default=False)
    is_set_image = fields.Boolean(string="Set Image ?", default=True)
    sync_images_with_product = fields.Boolean("Sync Images?",
                                              help="Check if you want to import images along with products",
                                              default=True)
    sync_price_with_product=fields.Boolean("Sync Product Price?",help="Check if you want to import price along with products",default=True)
    is_show_debug_info=fields.Boolean('Show Debug Information?',default=False)
    inventory_adjustment_id=fields.Many2one('stock.inventory',"Last Inventory")
    visible = fields.Boolean("Visible on the product page?",default=True,help="""Attribute is visible on the product page""")
    variation = fields.Boolean("Attribute used as a variations?",default=True,help="""Attribute can be used as variation?""")
    attribute_type=fields.Selection([('select', 'Select'), ('text', 'Text')], string='Attribute Type',default='text')
    #Account Field
    woo_property_account_payable_id = fields.Many2one('account.account',string="Account Payable",help='This account will be used instead of the default one as the payable account for the current partner')
    woo_property_account_receivable_id = fields.Many2one('account.account',string="Account Receivable",help='This account will be used instead of the default one as the receivable account for the current partner')
    last_synced_order_date = fields.Datetime(string="Last Date of Import Order",help="Which from date to import woo order from woo commerce")
    
    def _count_all(self):
        for instance in self:
            instance.product_count = len(instance.product_ids)
            instance.sale_order_count = len(instance.sale_order_ids)
            instance.picking_count = len(instance.picking_ids)
            instance.invoice_count = len(instance.invoice_ids)
            instance.exported_product_count = len(instance.exported_product_ids)
            instance.ready_to_expor_product_count = len(instance.ready_to_expor_product_ids)
            instance.published_product_count = len(instance.published_product_ids)
            instance.unpublished_product_count = len(instance.unpublished_product_ids)
            instance.quotation_count = len(instance.quotation_ids)
            instance.order_count = len(instance.order_ids)
            instance.confirmed_picking_count = len(instance.confirmed_picking_ids)
            instance.assigned_picking_count = len(instance.assigned_picking_ids)
            instance.partially_available_picking_count = len(instance.partially_available_picking_ids)
            instance.done_picking_count = len(instance.done_picking_ids)
            instance.open_invoice_count = len(instance.open_invoice_ids)
            instance.paid_invoice_count = len(instance.paid_invoice_ids)
            instance.refund_invoice_count = len(instance.refund_invoice_ids)  
            instance.coupons_count = len(instance.coupons_ids)          
    
    color = fields.Integer(string='Color Index')
    
    exported_product_ids = fields.One2many('woo.product.template.ept','woo_instance_id',domain=[('exported_in_woo','=',True)],string="Exported Products")
    exported_product_count = fields.Integer(compute='_count_all', string="Exported Products Count")
    
    ready_to_expor_product_ids = fields.One2many('woo.product.template.ept','woo_instance_id',domain=[('exported_in_woo','=',False)],string="Ready To Export")
    ready_to_expor_product_count = fields.Integer(compute='_count_all', string="Ready To Export Count")
    
    published_product_ids = fields.One2many('woo.product.template.ept','woo_instance_id',domain=[('website_published','=',True)],string="Published")
    published_product_count = fields.Integer(compute='_count_all', string="Published Count")
    
    unpublished_product_ids = fields.One2many('woo.product.template.ept','woo_instance_id',domain=[('website_published','=',False),('exported_in_woo','=',True)],string="UnPublished")
    unpublished_product_count = fields.Integer(compute='_count_all', string="UnPublished Count")
    
    quotation_ids = fields.One2many('sale.order','woo_instance_id',domain=[('state','in',['draft','sent'])],string="Quotations")        
    quotation_count = fields.Integer(compute='_count_all', string="Quotations Count")
        
    order_ids = fields.One2many('sale.order','woo_instance_id',domain=[('state','not in',['draft','sent','cancel'])],string="Sales Order")
    order_count = fields.Integer(compute='_count_all', string="Sales Order Count")
    
    coupons_ids = fields.One2many('woo.coupons.ept','woo_instance_id',domain=[('exported_in_woo','=',True)],string="Coupons")
    coupons_count = fields.Integer(compute='_count_all', string="Coupons Count")
    
    confirmed_picking_ids = fields.One2many('stock.picking','woo_instance_id',domain=[('state','=','confirmed')],string="Confirm Pickings")
    confirmed_picking_count =fields.Integer(compute='_count_all', string="Confirm Pickings Counts")
    assigned_picking_ids = fields.One2many('stock.picking','woo_instance_id',domain=[('state','=','assigned')],string="Assigned Pickings")
    assigned_picking_count =fields.Integer(compute='_count_all', string="Assigned Pickings Counts")
    partially_available_picking_ids = fields.One2many('stock.picking','woo_instance_id',domain=[('state','=','partially_available')],string="Partially Available Pickings")
    partially_available_picking_count =fields.Integer(compute='_count_all', string="Partially Available Pickings Count")
    done_picking_ids = fields.One2many('stock.picking','woo_instance_id',domain=[('state','=','done')],string="Done Pickings")
    done_picking_count =fields.Integer(compute='_count_all', string="Done Pickings Count")
    
    open_invoice_ids = fields.One2many('account.invoice','woo_instance_id',domain=[('state','=','open'),('type','=','out_invoice')],string="Open Invoices")
    open_invoice_count =fields.Integer(compute='_count_all', string="Open Invoices Count")    

    paid_invoice_ids = fields.One2many('account.invoice','woo_instance_id',domain=[('state','=','paid'),('type','=','out_invoice')],string="Paid Invoices")
    paid_invoice_count =fields.Integer(compute='_count_all', string="Paid Invoices Count")
    
    refund_invoice_ids = fields.One2many('account.invoice','woo_instance_id',domain=[('type','=','out_refund')],string="Refund Invoices")
    refund_invoice_count =fields.Integer(compute='_count_all', string="Refund Invoices Count")
    
    product_ids = fields.One2many('woo.product.template.ept','woo_instance_id',string="Products")
    product_count = fields.Integer(compute='_count_all', string="Products Count")
    
    sale_order_ids = fields.One2many('sale.order','woo_instance_id',string="Orders")
    sale_order_count = fields.Integer(compute='_count_all', string="Orders Count")
    
    picking_ids = fields.One2many('stock.picking','woo_instance_id',string="Pickings")
    picking_count = fields.Integer(compute='_count_all', string="Pickings Count")
    
    invoice_ids = fields.One2many('account.invoice','woo_instance_id',string="Invoices")
    invoice_count = fields.Integer(compute='_count_all', string="Invoices Count")

    global_channel_id = fields.Many2one('global.channel.ept', string="Global Channel")

    currency_id = fields.Many2one("res.currency", string="Currency",
                                  help="Woo Commerce Currency.")  # Currency Field Added By : Ajay Ghimre on 12 Nov 2018.
    auto_active_currency = fields.Boolean("Auto Active Currency", default=True,
                                          help="Automatically changes currency state to active if it is inactive.")  # Auto Active Currency Field Added By : Ajay Ghimre on 12 Nov 2018.

    @api.model
    def create(self, vals):
        res = super(woo_instance_ept, self).create(vals)
        res.set_woo_current_currency_data()
        pricelist = res.create_woo_pricelist()
        sales_channel = res.create_sales_channel()
        global_channel = res.create_global_channel()

        vals = {
            'pricelist_id': pricelist.id,
            'section_id': sales_channel.id,
            'global_channel_id': global_channel.id
        }
        res.write(vals)

        return res

    def create_global_channel(self):
        global_channel_obj = self.env['global.channel.ept']
        vals = {
            'name': self.name
        }
        global_channel = global_channel_obj.create(vals)
        return global_channel

    def create_sales_channel(self):
        crm_team_obj = self.env['crm.team']
        vals = {
            'name': self.name,
            'team_type': 'sales',
            'use_quotations': True
        }
        sales_channel = crm_team_obj.create(vals)
        return sales_channel

    def create_woo_pricelist(self):
        pricelist_obj = self.env['product.pricelist']
        vals = {
            'name': "Woo {} Pricelist".format(self.name),
            'currency_id': self.currency_id and self.currency_id.id or False
        }
        pricelist = pricelist_obj.create(vals)
        return pricelist

    @api.multi
    def test_woo_connection(self):
        wcapi = self.connect_in_woo()
        r = wcapi.get("products")
        if not isinstance(r, requests.models.Response):
            raise Warning(_("Response is not in proper format :: %s" % (r)))
        if r.status_code != 200:
            raise Warning(_("%s\n%s" % (r.status_code, r.reason)))
        else:
            self.env['woo.payment.gateway'].get_payment_gateway(self)
            self.create_financial_status('paid')
            self.create_financial_status('not_paid')
            self._cr.commit()
            raise Warning('Service working properly')
        return True

    def set_woo_current_currency_data(self):
        currency = self.get_woo_currency()
        self.currency_id = currency and currency.id or self.env.user.currency_id.id or False
        return True

    def create_financial_status(self,financial_status):
        payment_methods = self.env['woo.payment.gateway'].search([('woo_instance_id','=',self.id)])
        financial_status_obj = self.env["woo.sale.auto.workflow.configuration"]
        auto_workflow_record = self.env.ref("auto_invoice_workflow_ept.automatic_validation_ept")
        for payment_method in payment_methods:
            domain=[
                ('woo_instance_id','=',self.id),
                ('payment_gateway_id','=',payment_method.id),
                ('financial_status','=',financial_status)
            ]
            existing_financial_status = financial_status_obj.search(domain)

            if existing_financial_status:
                continue

            vals={
                'woo_instance_id':self.id,
                'auto_workflow_id':auto_workflow_record.id,
                'payment_gateway_id':payment_method.id,
                'financial_status':financial_status
            }
            financial_status_obj.create(vals)
        return True
        
    @api.multi
    def reset_to_confirm(self):
        self.write({'state':'not_confirmed'})
        return True
    
    @api.multi
    def confirm(self):        
        wcapi = self.connect_in_woo()
        r = wcapi.get("products")
        if not isinstance(r,requests.models.Response):
            raise Warning(_("Response is not in proper format :: %s"%(r)))
        if r.status_code != 200:
            raise Warning(_("%s\n%s"%(r.status_code,r.reason)))
        else:            
            self.write({'state':'confirmed'})
        return True              
        
    @api.model
    def connect_in_woo(self):
        host = self.host
        consumer_key = self.consumer_key
        consumer_secret = self.consumer_secret
        wp_api = True if self.woo_version == 'new' else False
        version = "wc/v1" if wp_api else "v3"
        if self.is_latest:
            version = "wc/v2"
        wcapi = woocommerce.api.API(url=host, consumer_key=consumer_key,
                    consumer_secret=consumer_secret,verify_ssl=self.verify_ssl,wp_api=wp_api,version=version,query_string_auth=True)
        return wcapi

    @api.model
    def get_woo_currency(self):
        transaction_log_obj = self.env["woo.transaction.log"]
        currency_obj = self.env['res.currency']
        response = self.sync_system_status(transaction_log_obj)
        if response.get('settings', False):
            currency_code = response.get('settings').get('currency', False)
            currency_symbol = response.get('settings').get('currency_symbol', False)

            if not currency_code:
                transaction_log_obj.create(
                    {'message': "Import Woo System Status \nCurrency Code Not Received in Reponse",
                     'mismatch_details': True,
                     'type': 'system_status',
                     'woo_self_id': self.id
                     })

            if not currency_symbol:
                transaction_log_obj.create(
                    {'message': "Import Woo System Status \nCurrency Symbol Not Received in Reponse",
                     'mismatch_details': True,
                     'type': 'system_status',
                     'woo_self_id': self.id
                     })

            currency = currency_obj.search([
                ('name', '=', currency_code)
            ])

            if not currency and self.auto_active_currency:
                currency = currency_obj.search([
                    ('name', '=', currency_code),
                    ('active', '!=', True)
                ])
                currency.active = True
            if not currency:
                raise Warning(
                    "Currency {} not found in odoo.\nPlease make sure currency record is created for {} and is in active state.".format(
                        currency_code, currency_code))
            return currency

    def sync_system_status(self, transaction_log_obj):
        wcapi = self.connect_in_woo()
        if self.woo_version == 'new':
            res = wcapi.get("system_status")
        else:
            res = wcapi.get("system_status")  # This api does not have system_status property.
        if not isinstance(res, requests.models.Response):
            transaction_log_obj.create(
                {'message': "Import Woo System Status \nResponse is not in proper format :: %s" % (res),
                 'mismatch_details': True,
                 'type': 'system_status',
                 'woo_self_id': self.id
                 })
            return {}
        if res.status_code not in [200, 201]:
            message = "Error in Import Woo System Status %s" % (res.content)
            transaction_log_obj.create(
                {'message': message,
                 'mismatch_details': True,
                 'type': 'system_status',
                 'woo_self_id': self.id
                 })
            return {}
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create({
                                           'message': "Json Error : While import system status from WooCommerce for self %s. \n%s" % (
                                           self.name, e),
                                           'mismatch_details': True,
                                           'type': 'system_status',
                                           'woo_self_id': self.id
                                           })
            return []
        if self.woo_version == 'old':
            errors = response.get('errors', '')
            if errors:
                message = errors[0].get('message')
                transaction_log_obj.create(
                    {'message': message,
                     'mismatch_details': True,
                     'type': 'system_status',
                     'woo_self_id': self.id
                     })
                return []
            return response
        elif self.woo_version == 'new':
            return response
