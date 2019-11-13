from odoo import models,fields,api,_
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

class sale_order(models.Model):
    _inherit="sale.order"

    @api.multi
    def delivery_set(self):
        if self.woo_order_id:
            raise Warning(_('You are not allow to change manually shipping charge in WooCommerce order.'))
        else:
            super(sale_order,self).delivery_set()    
            
    @api.one
    def _get_woo_order_status(self):
        for order in self:
            flag=False
            for picking in order.picking_ids:
                if picking.state!='cancel':
                    flag=True
                    break   
            if not flag:
                continue
            if order.picking_ids:
                order.updated_in_woo=True
            else:
                order.updated_in_woo=False
            for picking in order.picking_ids:
                if picking.state =='cancel':
                    continue
                if picking.picking_type_id.code!='outgoing':
                    continue
                if not picking.updated_in_woo:
                    order.updated_in_woo=False
                    break

    def _search_woo_order_ids(self,operator,value):
        query="""
                select sale_order.id from stock_picking 
                inner join sale_order on sale_order.procurement_group_id=stock_picking.group_id                    
                inner join stock_location on stock_location.id=stock_picking.location_dest_id and stock_location.usage='customer'
                where stock_picking.updated_in_woo=False and stock_picking.state='done'
                """
        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids=[]
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        order_ids = list(set(order_ids))
        return [('id','in',order_ids)]

    @api.multi
    def visibl_transaction_id(self):
        for order in self:
            if order.woo_instance_id.woo_version == "new":
                order.visible_trans_id=True
            else:
                order.visible_trans_id=False    
    
    woo_order_id=fields.Char("Woo Order Reference",help="WooCommerce Order Reference")
    woo_order_number=fields.Char("Order Number",help="WooCommerce Order Number")
    auto_workflow_process_id=fields.Many2one("sale.workflow.process.ept","Auto Workflow")           
    updated_in_woo=fields.Boolean("Updated In woo",compute='_get_woo_order_status',search='_search_woo_order_ids')
    woo_instance_id=fields.Many2one("woo.instance.ept","Woo Instance")
    payment_gateway_id=fields.Many2one("woo.payment.gateway","Woo Payment Gateway")
    woo_trans_id=fields.Char("Transaction Id",help="WooCommerce Order Transaction Id")
    woo_customer_ip=fields.Char("Customer IP",help="WooCommerce Customer IP Address")
    visible_trans_id=fields.Boolean("trans_id_avail",compute=visibl_transaction_id,store=False)        
    
    @api.multi
    def create_or_update_woo_customer(self,woo_cust_id,vals,is_company=False,parent_id=False,type=False,instance=False):
        country_obj=self.env['res.country']
        state_obj=self.env['res.country.state']
        partner_obj=self.env['res.partner']
        
        first_name=vals.get('first_name')
        last_name=vals.get('last_name')
        
        if not first_name and not last_name:
            return False
        
        city=vals.get('city')
        
        name = "%s %s"%(first_name,last_name)
        
        
        company_name=vals.get("company")
        
        if company_name and not parent_id:
            is_company=True
        
        email=vals.get('email')                      
        phone=vals.get("phone")                                  
        zip=vals.get('postcode')            
        
        
        address1=vals.get('address_1')
        address2=vals.get('address_2')
        country_name=vals.get('country')
        state_name = vals.get('state')
        
        woo_customer_id = woo_cust_id
        woo_customer_id = "%s_%s"%(instance.id,woo_customer_id) if woo_customer_id else False 
                             
        country=country_obj.search([('code','=',country_name)],limit=1)
        if not country:
            country=country_obj.search([('name','=',country_name)],limit=1)
            
        if not country:
            state=state_obj.search(["|", ('code', '=', state_name),('name','=',state_name)],limit=1)            
        else:
            state = state_obj.search(["|", ('code', '=', state_name), ('name', '=', state_name), ('country_id', '=', country.id)],limit=1)           
                        
#         vals={'woo_customer_id':woo_customer_id}
#         keys=['woo_customer_id']
#         partner = partner_obj._find_partner(vals, key_list=keys)
        partner=partner_obj.search([('woo_customer_id','=',woo_customer_id)],limit=1) if woo_customer_id else False
        if not partner:
            partner=partner_obj.search([('name','=',name),('city','=',city),('street','=',address1),('street2','=',address2),('email','=',email),('phone','=',phone),('zip','=',zip),('country_id','=',country.id),('state_id','=',state.id)],limit=1)
#             vals = {'name':name, 'city':city, 'street':address1, 'street2':address2, 'email':email, 'phone':phone, 'zip':zip, 'country_id':country.id, 'state_id':state.id}
#             keys = ['name','city','street','street2','email','phone','zip','country_id','state_id']
#             partner = partner_obj._find_partner(vals, key_list=keys)

        if partner:
            partner_vals={'state_id':state and state.id or False,'is_company':is_company,'woo_company_name_ept':company_name or partner.woo_company_name_ept,
                           'phone':phone or partner.phone,'woo_customer_id':woo_customer_id or partner.woo_customer_id,
                           'lang':instance.lang_id.code,'name':partner.name,
                           'property_product_pricelist':instance.pricelist_id.id,
                           'property_account_position_id':instance.fiscal_position_id and instance.fiscal_position_id.id or False,
                           'property_payment_term_id':instance.payment_term_id and instance.payment_term_id.id or False,'email':email or False}
            partner_vals.update({'property_account_payable_id':instance.woo_property_account_payable_id.id,'property_account_receivable_id':instance.woo_property_account_receivable_id.id})
            
#             woo_partner_vals = partner_obj._prepare_partner_vals(partner_vals)
#             woo_partner_vals.update({
#                 'woo_company_name_ept': company_name or partner.woo_company_name_ept,
#                 'woo_customer_id': woo_customer_id or partner.woo_customer_id,
#             })
            partner.write(partner_vals)
        else:
            partner_vals={'type':type,'parent_id':parent_id,'woo_customer_id':woo_customer_id or '',
                                        'name':name,'state_id':state and state.id or False,'city':city,
                                        'street':address1,'street2':address2,
                                        'phone':phone,'zip':zip,'email':email,
                                        'country_id':country and country.id or False,'is_company':is_company,
                                        'lang':instance.lang_id.code,
                                        'property_product_pricelist':instance.pricelist_id.id,
                                        'property_account_position_id':instance.fiscal_position_id and instance.fiscal_position_id.id or False,
                                        'property_payment_term_id':instance.payment_term_id and instance.payment_term_id.id or False,
                                        'woo_company_name_ept':company_name}
            partner_vals.update({'property_account_payable_id':instance.woo_property_account_payable_id.id,'property_account_receivable_id':instance.woo_property_account_receivable_id.id})
            partner=partner_obj.create(partner_vals)
        return partner
   
    @api.model
    def createWooAccountTax(self,value,price_included,company,title):
        accounttax_obj = self.env['account.tax']
        
        if price_included:
            name='%s_(%s %s included %s)_%s'%(title,str(value),'%',price_included and 'T' or 'F',company.name)
        else:
            name='%s_(%s %s excluded %s)_%s'%(title,str(value),'%',price_included and 'F' or 'T',company.name)            

        accounttax_id = accounttax_obj.create({'name':name,'amount':float(value),'type_tax_use':'sale','price_include':price_included,'company_id':company.id})
        
        return accounttax_id

    @api.model
    def get_woo_tax_id_ept(self,instance,tax_datas,tax_included):
        tax_id=[]        
        taxes=[]
        for tax in tax_datas:
            rate=float(tax.get('rate',0.0))
            if rate!=0.0:
                acctax_id = self.env['account.tax'].search([('price_include','=',tax_included),('type_tax_use', '=', 'sale'), ('amount', '=', rate),('company_id','=',instance.warehouse_id.company_id.id)],limit=1)
                if not acctax_id:
                    acctax_id = self.createWooAccountTax(rate,tax_included,instance.warehouse_id.company_id,tax.get('name'))
                    if acctax_id:
                        transaction_log_obj=self.env["woo.transaction.log"]
                        message="""Tax was not found in ERP ||
                        Automatic Created Tax,%s ||
                        tax rate  %s ||
                        Company %s"""%(acctax_id.name,rate,instance.company_id.name)                                                                                                                                                                                                                                 
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'sales',
                                                     'woo_instance_id':instance.id
                                                    })                    
                if acctax_id:
                    taxes.append(acctax_id.id)
        if taxes:
            tax_id = [(6, 0, taxes)]

        return tax_id
    
    @api.model
    def check_woo_mismatch_details(self,lines,instance,order_number):
        transaction_log_obj=self.env["woo.transaction.log"]
        odoo_product_obj=self.env['product.product']
        woo_product_obj=self.env['woo.product.product.ept']
        woo_product_template_obj = self.env['woo.product.template.ept']
        mismatch=False
        for line in lines:
            line_product_id=False
            if instance.woo_version == 'old':
                line_product_id=line.get('product_id',False)
            elif instance.woo_version == 'new':
                line_product_id=line.get('product_id',False) or line.get('variation_id',False)
                line_product_sku = line.get('sku', False)
                if not line_product_sku:
                    transaction_log_obj.create({
                        'message': "Order %s not imported because Sku not found in Product : %s of ID : %s ." % (
                            order_number, line.get('name', False),
                            line.get('product_id', False)),
                        'mismatch_details': True,
                        'type': 'sales',
                        'woo_instance_id': instance.id
                    })
                    mismatch = True
                    break

            barcode=0
            odoo_product=False
            woo_variant=False
            if line_product_id:
                woo_variant=woo_product_obj.search([('variant_id','=',line_product_id),('woo_instance_id','=',instance.id)],limit=1)                
                if woo_variant:
                    continue
                try:
                    if line_product_id:
                        wcapi = instance.connect_in_woo()
                        res=wcapi.get('products/%s'%line_product_id)
                        if not isinstance(res,requests.models.Response):               
                            transaction_log_obj.create({'message': "Get Product \nResponse is not in proper format :: %s"%(res),
                                                         'mismatch_details':True,
                                                         'type':'sales',
                                                         'woo_instance_id':instance.id
                                                        })
                            mismatch=True
                            break    
                        try:                    
                            woo_variant = res.json()
                        except Exception as e:
                            transaction_log_obj.create({'message':"Json Error : While import Product with id %s from WooCommerce for instance %s. \n%s"%(line_product_id,instance.name,e),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
                            continue                        
                        if instance.woo_version == 'old':
                            errors = woo_variant.get('errors','')
                            if errors:
                                message = errors[0].get('message')
                                transaction_log_obj.create(
                                                            {'message':"Product Removed from WooCommerce site,  %s"%(message),
                                                             'mismatch_details':True,
                                                             'type':'product',
                                                             'woo_instance_id':instance.id
                                                            })
                    else:
                        woo_variant = False
                except:
                    woo_variant=False
                    message="Variant Id %s not found in woo || default_code %s || order ref %s"%(line_product_id,line.get('sku'),order_number)
                    log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                    if not log:
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'sales',
                                                     'woo_instance_id':instance.id
                                                    })

                if woo_variant:
                    if instance.woo_version == 'old':                    
                        barcode=woo_variant.get('product',{}).get('sku')
                    elif instance.woo_version == 'new':
                        barcode=woo_variant.get('sku')
                else:
                    barcode=0
            sku=line.get('sku') or ''
            woo_variant=barcode and woo_product_obj.search([('product_id.default_code','=',barcode),('woo_instance_id','=',instance.id)],limit=1)
            if not woo_variant:
                odoo_product=barcode and odoo_product_obj.search([('default_code','=',barcode)],limit=1) or False
            if not odoo_product and not woo_variant:
                woo_variant=sku and woo_product_obj.search([('default_code','=',sku),('woo_instance_id','=',instance.id)],limit=1)
                if not woo_variant:
                    odoo_product=sku and odoo_product_obj.search([('default_code','=',sku)],limit=1)
            
            if not odoo_product:
                if instance.woo_version=="new" and line_product_id: 
                        woo_product_template_obj.sync_new_products(instance,line_product_id)
                        odoo_product = odoo_product_obj.search([('default_code','=',sku)],limit=1) 
                if instance.woo_version=="old" and line_product_id: 
                        woo_product_template_obj.sync_products(instance,line_product_id)
                        odoo_product = odoo_product_obj.search([('default_code','=',sku)],limit=1)
                
            if not woo_variant and not odoo_product:
                message="%s Product Code Not found for order %s"%(sku,order_number)
                log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                if not log:
                    transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'sales',
                                                 'woo_instance_id':instance.id
                                                })
                mismatch=True
                break
        return mismatch

    @api.model
    def create_woo_sale_order_line(self,line,tax_ids,product,quantity,fiscal_position,partner,pricelist_id,name,order,price,is_shipping=False):
        sale_order_line_obj=self.env['sale.order.line']
        uom_id=product and product.uom_id and product.uom_id.id or False
        product_data={
                      'product_id':product and product.ids[0] or False,
                      'order_id':order.id,
                      'company_id':order.company_id.id,
                      'product_uom':uom_id,
                      'name':name,
                      'producturl':line.get('product_url') or False
                    }
        tmp_rec = sale_order_line_obj.new(product_data)
        tmp_rec.product_id_change()
        so_line_vals=sale_order_line_obj._convert_to_write({name: tmp_rec[name] for name in tmp_rec._cache})
        if tax_ids:
            tax_ids = tax_ids and self.env['account.tax'].search([('id','in',tax_ids[0][2])])
        if fiscal_position:
            tax_ids = fiscal_position.map_tax(tax_ids, product[0], order.partner_id) if fiscal_position else tax_ids
        so_line_vals.update(
                            {
                            'order_id':order.id,
                            'order_qty':quantity,
                            'price_unit':price,
                            'woo_line_id':line.get('id'),
                            'is_delivery':is_shipping,
                            'tax_id':tax_ids and [(6,0,tax_ids.ids)] or [(6,0,[])],
                            }                                    
                            )                                                                      
        woo_so_line_vals=sale_order_line_obj.create_sale_order_line_ept(so_line_vals)
        woo_so_line_vals.update({'woo_line_id':line.get('id')})
        woo_so_line_vals.update({'tax_id': tax_ids and [(6, 0, tax_ids.ids)] or [(6, 0, [])]})
        line=sale_order_line_obj.create(woo_so_line_vals)
        return line

    @api.model
    def create_or_update_woo_product(self,line,instance,wcapi):
        transaction_log_obj=self.env["woo.transaction.log"]
        woo_product_tmpl_obj=self.env['woo.product.template.ept']
        woo_product_obj=self.env['woo.product.product.ept']        
        variant_id=False
        if instance.woo_version == 'old':
            variant_id=line.get('product_id')
        elif instance.woo_version == 'new':
            variant_id=line.get('variation_id',False) or line.get('product_id',False)
        woo_product=False
        if variant_id:
            woo_product=woo_product_obj.search([('woo_instance_id','=',instance.id),('variant_id','=',variant_id)],limit=1)
            if woo_product:
                return woo_product
            woo_product=woo_product_obj.search([('woo_instance_id','=',instance.id),('default_code','=',line.get('sku'))],limit=1)
            woo_product and woo_product.write({'variant_id':variant_id})
            if woo_product:
                return woo_product
            response=wcapi.get('products/%s'%(variant_id))
            if not isinstance(response,requests.models.Response):               
                transaction_log_obj.create({'message': "Get Product \nResponse is not in proper format :: %s"%(response),
                                             'mismatch_details':True,
                                             'type':'sales',
                                             'woo_instance_id':instance.id
                                            })
                return False           
            try:
                res = response.json()
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While import Product with id %s from WooCommerce for instance %s. \n%s"%(variant_id,instance.name,e),
                             'mismatch_details':True,
                             'type':'sales',
                             'woo_instance_id':instance.id
                            })
                return False
            
            parent_id = False
            if instance.woo_version == 'old':
                result = res.get('product')
                parent_id = result.get('parent_id',False)
                if not parent_id:
                    parent_id = variant_id
                woo_product_tmpl_obj.sync_products(instance,parent_id,update_templates=True)
            elif instance.woo_version == 'new':
                parent_id = res.get('parent_id',False)
                if not parent_id:
                    parent_id = variant_id
                woo_product_tmpl_obj.sync_new_products(instance,parent_id,update_templates=True)                        
            woo_product=woo_product_obj.search([('woo_instance_id','=',instance.id),('variant_id','=',variant_id)],limit=1)
        else:
            woo_product=woo_product_obj.search([('woo_instance_id','=',instance.id),('default_code','=',line.get('sku'))],limit=1)
            if woo_product:
                return woo_product
        return woo_product

    @api.multi
    def create_or_update_payment_gateway(self,instance,result):
        payment_gateway_obj=self.env["woo.payment.gateway"]
        payment_gateway = False
        vals=""    
        payment_data = ""
        code = ""
        name = ""
        
        if instance.woo_version == "old":
            payment_data = result.get("payment_details")
            code = payment_data.get("method_id")
            name = payment_data.get("method_title")
        else:
            code = result.get("payment_method")
            name = result.get("payment_method_title")
            
        if not code:
            return False
        payment_gateway = payment_gateway_obj.search([("code","=",code),("woo_instance_id","=",instance.id)],limit=1)
        if payment_gateway:
            vals={"name":name}
            payment_gateway.write(vals)
        else:
            vals={"code":code,"name":name,"woo_instance_id":instance.id}
            payment_gateway = payment_gateway_obj.create(vals)
        return payment_gateway

    @api.model
    def get_woo_order_vals(self,result,workflow,invoice_address,instance,partner,shipping_address,pricelist_id,fiscal_position,payment_term,payment_gateway):
            woo_order_number = ''
            note = ''
            created_at = False
            if instance.woo_version == 'old':
                woo_order_number = result.get('order_number')
                note = result.get('note')
                created_at = result.get('created_at')
                woo_trans_id = ""
                woo_customer_ip = result.get("customer_ip")
            elif instance.woo_version == 'new':
                woo_order_number = result.get('number')
                note = result.get('customer_note')
                created_at = result.get('date_created')     
                woo_trans_id = result.get("transaction_id")
                woo_customer_ip = result.get("customer_ip_address")

            # Edited by jigneshb
            if instance.order_prefix:
                name="%s%s"%(instance.order_prefix,woo_order_number)
            elif not instance.use_custom_order_prefix:
                name=self.env['ir.sequence'].next_by_code('sale.order') or _('New')
            else:
                name=woo_order_number
                
            ordervals = {               
                'partner_invoice_id' : invoice_address.ids[0],
                'date_order' :created_at,
                'warehouse_id' : instance.warehouse_id.id,
                'partner_id' : partner.ids[0],
                'partner_shipping_id' : shipping_address.ids[0],
                'state' : 'draft',
                'pricelist_id' : pricelist_id or instance.pricelist_id.id or False,
                'fiscal_position_id': fiscal_position and fiscal_position.id or False,
                'payment_term_id':payment_term or instance.payment_term_id.id or False, 
                }

            woo_order_vals = self.create_sales_order_vals_ept(ordervals)

            if workflow:
                if not workflow.picking_policy:
                    raise Warning("Please configure Sale Auto Workflow properly.")
                woo_order_vals.update({
                    'picking_policy' : workflow.picking_policy,
                    'auto_workflow_process_id':workflow.id,
                    'invoice_policy':workflow.invoice_policy
                    })

            # Edited by jigneshb because prefix is not working when use common connector library.
            woo_order_vals.update({
                'name': name,
                'note': note,
                'woo_order_id': result.get('id'),
                'woo_order_number': woo_order_number,
                'woo_instance_id': instance.id,
                'team_id': instance.section_id and instance.section_id.id or False,
                'company_id': instance.company_id.id,
                'payment_gateway_id': payment_gateway and payment_gateway.id or False,
                'woo_trans_id': woo_trans_id,
                'woo_customer_ip': woo_customer_ip,
                'global_channel_id': instance.global_channel_id and instance.global_channel_id.id or False,

            })

            return woo_order_vals

    def import_all_woo_orders(self,wcapi,instance,transaction_log_obj,order_status,page,after_date=False,before_date=False,is_cron=False):
        if instance.woo_version == 'new':
            if after_date and before_date:
                res = wcapi.get('orders?status=%s&per_page=100&page=%s&after=%s&before=%s'%(order_status.status,page,after_date,before_date))
            else:
                res = wcapi.get('orders?status=%s&per_page=100&page=%s'%(order_status.status,page))    
        else:
            if after_date and before_date:
                res = wcapi.get('orders?status=%s&per_page=100&page=%s&after=%s&before=%s'%(order_status.status,page,after_date,before_date))
            else:
                res = wcapi.get('orders?status=%s&filter[limit]=1000&page=%s'%(order_status.status,page))
        if not isinstance(res,requests.models.Response):               
            transaction_log_obj.create({'message': "Import All Orders \nResponse is not in proper format :: %s"%(res),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
            return []
        if res.status_code not in [200,201]:
            message = "Error in Import All Orders %s"%(res.content)                        
            transaction_log_obj.create(
                                {'message':message,
                                 'mismatch_details':True,
                                 'type':'sales',
                                 'woo_instance_id':instance.id
                                })
            return []
        try:
            response = res.json()
        except Exception as e:
            transaction_log_obj.create(
                                {'message':"Json Error : While import Orders from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'sales',
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
                                             'type':'sales',
                                             'woo_instance_id':instance.id
                                            })
                return []
            return response.get('orders')
        elif instance.woo_version == 'new':
            return response
    
    @api.model
    def auto_import_woo_sale_order_ept(self,ctx={}):
        woo_instance_obj=self.env['woo.instance.ept']
        if not isinstance(ctx,dict) or not 'woo_instance_id' in ctx:
            return True
        woo_instance_id = ctx.get('woo_instance_id',False)
        if woo_instance_id:
            instance=woo_instance_obj.search([('id','=',woo_instance_id),('state','=','confirmed')])
            if instance and instance.woo_version == 'old':
                after_date = instance.last_synced_order_date
                before_date = str(datetime.now())
                self.import_woo_orders(instance,before_date,after_date,is_cron=True)
            elif instance and instance.woo_version == 'new':
                after_date = instance.last_synced_order_date
                before_date = str(datetime.now())
                self.import_new_woo_orders(instance,before_date,after_date,is_cron=True)
        return True

    @api.model
    def verify_order(self,instance,order):
        payment_method = ""
        total = 0
        discount = 0
        
        if instance.woo_version == 'old':
            payment_method = order.get("payment_details").get("method_id")
            total = order.get("total")
            discount = order.get("total_discount")
        
        if instance.woo_version == 'new':
            payment_method = order.get("payment_method")
            total = order.get("total")
            if order.get("coupon_lines"):
                discount = order.get("coupon_lines")[0].get("discount")
                
        if not payment_method and float(total) == 0 or float(discount) > 0:
            return True
        else:
            return False 

    @api.model
    def import_woo_orders(self,instance=False,before_date=False,after_date=False,is_cron=False):
        instances=[]
        transaction_log_obj=self.env["woo.transaction.log"]
        if not instance:
            instances=self.env['woo.instance.ept'].search([('order_auto_import','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            wcapi = instance.connect_in_woo()
            order_ids = []
            try: 
                tax_included  = wcapi.get('').json().get('store').get('meta').get('tax_included') or False
            except Exception as e:
                transaction_log_obj.create({'message':"Json Error : While import Product Tax from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
            for order_status in instance.import_order_status_ids:
                instance.last_synced_order_date = before_date
                if before_date and after_date:
                    response = wcapi.get('orders?after=%s&before=%s&status=%s&per_page=100'%(after_date,before_date,order_status.status))
                else:
                    response = wcapi.get('orders?status=%s&filter[limit]=1000'%(order_status.status))
                if not isinstance(response,requests.models.Response):                
                    transaction_log_obj.create({'message': "Import Orders \nResponse is not in proper format :: %s"%(response),
                                                 'mismatch_details':True,
                                                 'type':'sales',
                                                 'woo_instance_id':instance.id
                                                })
                    continue                                    
                if response.status_code not in [200,201]:
                    message = "Error in Import Orders %s"%(response.content)                        
                    transaction_log_obj.create(
                                        {'message':message,
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                try:
                    order_response=response.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import Orders from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'sales',
                                 'woo_instance_id':instance.id
                                })
                    continue
                order_ids = order_ids + order_response.get('orders')
                total_pages = response.headers.get('X-WC-TotalPages')
                if int(total_pages) >=2:
                    for page in range(2,int(total_pages)+1):            
                        order_ids = order_ids + self.import_all_woo_orders(wcapi,instance,transaction_log_obj,order_status,page,after_date,before_date,is_cron)            
            
            import_order_ids=[]
            
            for order in order_ids:  
                if self.search([('woo_instance_id','=',instance.id),('woo_order_id','=',order.get('id')),('woo_order_number','=',order.get('order_number'))]):
                    continue
                lines=order.get('line_items')
                if self.check_woo_mismatch_details(lines,instance,order.get('order_number')):
                    continue
                financial_status = 'paid'
                if order.get('payment_details').get('paid'):
                    financial_status = 'paid'
                else:
                    financial_status = 'not_paid'
                
                no_payment_gateway = False   
                payment_gateway=self.create_or_update_payment_gateway(instance, order)
                
                if not payment_gateway:
                    no_payment_gateway = self.verify_order(instance,order)
                    if not no_payment_gateway:
                        message="Payment Gateway is not found for this order %s and financial status is %s"%(order.get('order_number'),financial_status)
                        log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                        if not log:
                            transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'sales',
                                                 'woo_instance_id':instance.id
                                                })  
                        continue
                
                workflow = False
                if not no_payment_gateway and payment_gateway:
                    workflow_config=self.env['woo.sale.auto.workflow.configuration'].search([('woo_instance_id','=',instance.id),('financial_status','=',financial_status),('payment_gateway_id','=',payment_gateway.id)],limit=1)
                    workflow=workflow_config and workflow_config.auto_workflow_id or False
                
                if not workflow and not no_payment_gateway:                    
                    message="Workflow Configuration not found for this order %s, financial status is %s and Payment Gateway is %s"%(order.get('order_number'),financial_status,order.get('payment_details').get('method_id'))
                    log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                    if not log:
                        transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'sales',
                                             'woo_instance_id':instance.id
                                            })                    
                    continue
                woo_customer_id = order.get('customer',{}).get('id',False)
                partner=order.get('billing_address',False) and self.create_or_update_woo_customer(woo_customer_id,order.get('billing_address'), False, False,False,instance)
                if not partner:                    
                    message="Customer Not Available In %s Order"%(order.get('order_number'))
                    log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                    if not log:
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'sales',
                                                     'woo_instance_id':instance.id
                                                    })
                    continue
                shipping_address=order.get('shipping_address',False) and self.create_or_update_woo_customer(False,order.get('shipping_address'), False,partner.id,'delivery',instance) or partner                                                
                new_record = self.new({'partner_id':partner.id})
                new_record.onchange_partner_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})
                new_record = self.new(retval)
                new_record.onchange_partner_shipping_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})
                fiscal_position=partner.property_account_position_id 
                pricelist_id=retval.get('pricelist_id',False)
                payment_term=retval.get('payment_term_id')
                
                woo_order_vals = self.get_woo_order_vals(order, workflow, partner, instance, partner, shipping_address, pricelist_id, fiscal_position, payment_term, payment_gateway)
                sale_order = self.create(woo_order_vals) if woo_order_vals else False
                
                if not sale_order:
                    continue

                def calclulate_line_discount(line):
                    return (float(line.get('subtotal')) - float(line.get('total'))) + (float(line.get('subtotal_tax')) - float(line.get('total_tax')))
                
                order_discount = False
                discount_value = 0.0
                total_discount=float(order.get('total_discount',0.0))
                if float(total_discount)>0.0:
                    order_discount = True
                    if not tax_included:
                        discount_value = float(total_discount)
                
                import_order_ids.append(sale_order.id)                
                shipping_taxable = False
                tax_datas = []
                tax_ids = []
                for tax_line in order.get('tax_lines'):
                    tax_data = {}
                    rate_id = tax_line.get('rate_id')
                    if rate_id:
                        res_rate = wcapi.get('taxes/%s'%(rate_id))
                        try:
                            rate = res_rate.json()
                        except Exception as e:
                            transaction_log_obj.create({'message':"Json Error : While retrive Product tax id %s from WooCommerce for instance %s. \n%s"%(rate_id,instance.name,e),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
                            continue
                        tax_data = rate.get('tax',{})
                        tax_datas.append(tax_data)
                        shipping_taxable = tax_data.get('shipping')                       
                tax_ids = self.get_woo_tax_id_ept(instance,tax_datas,tax_included)
                for line in lines:                    
                    woo_product=self.create_or_update_woo_product(line,instance,wcapi)
                    if not woo_product:
                        continue
                    product=woo_product.product_id
                    actual_unit_price = 0.0                    
                    if tax_included:
                        actual_unit_price=(float(line.get('subtotal_tax')) + float(line.get('subtotal'))) / float(line.get('quantity'))                            
                    else:
                        actual_unit_price = float(line.get('subtotal')) / float(line.get('quantity'))
                    if tax_included and float(total_discount)>0.0:
                        discount_value += calclulate_line_discount(line) if order_discount else 0.0                                                                            
                    self.create_woo_sale_order_line(line,tax_ids,product,line.get('quantity'),fiscal_position,partner,pricelist_id,product.name,sale_order,actual_unit_price,False)                   
    
                shipping_tax_ids = []                     
                for line in order.get('shipping_lines',[]):
                    if shipping_taxable and float(order.get('shipping_tax')) > 0.0:                        
                        shipping_tax_ids =  self.get_woo_tax_id_ept(instance,tax_datas,False)
                    else:
                        shipping_tax_ids = []
                        
                    delivery_method=line.get('method_title')
                    if delivery_method:
                        carrier=self.env['delivery.carrier'].search([('woo_code','=',delivery_method)],limit=1)
                        if not carrier:
                            carrier=self.env['delivery.carrier'].search([('name','=',delivery_method)],limit=1)
                        if not carrier:
                            carrier=self.env['delivery.carrier'].search(['|',('name','ilike',delivery_method),('woo_code','ilike',delivery_method)],limit=1)
                        if not carrier:
                            carrier=self.env['delivery.carrier'].create({'name':delivery_method,'woo_code':delivery_method,'fixed_price':line.get('total')})
                        sale_order.write({'carrier_id':carrier.id})
                        if carrier.product_id:
                            shipping_product=carrier.product_id
                    line=self.create_woo_sale_order_line(line,shipping_tax_ids,shipping_product,1,fiscal_position,partner,pricelist_id,shipping_product and shipping_product.name or line.get('method_title'),sale_order,line.get('total'),True)
                if order_discount and discount_value:                                                                                                                            
                    self.create_woo_sale_order_line({},tax_ids,instance.discount_product_id,1,fiscal_position,partner,pricelist_id,instance.discount_product_id.name,sale_order,discount_value*-1,False)
                fee_lines = order.get("fee_lines",[])
                for fee_line in fee_lines:
                    fee_value = fee_line.get("total")
                    fee = fee_line.get("title")
                    fee_line_tax_ids = []
                    fee_line_tax_ids =  self.get_woo_tax_id_ept(instance,tax_datas,False)
                    if fee_value:
                        self.create_woo_sale_order_line({},fee_line_tax_ids,instance.fee_line_id,1,fiscal_position,partner,pricelist_id,fee,sale_order,fee_value,False)
            if import_order_ids:
                self.env['sale.workflow.process.ept'].auto_workflow_process(ids=import_order_ids)
                odoo_orders=self.browse(import_order_ids)
                for order in odoo_orders:
                    order.invoice_shipping_on_delivery=False
        return True
    
    @api.model
    def import_new_woo_orders(self,instance=False,before_date=False,after_date=False,is_cron=True):
        """
        @Modify by :Haresh Mori on date 22/04/2019
        Add new functionality to import order base on date wise.
        """
        instances=[]
        transaction_log_obj=self.env["woo.transaction.log"]
        if not instance:
            instances=self.env['woo.instance.ept'].search([('order_auto_import','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            wcapi = instance.connect_in_woo()             
            order_ids = []
            for order_status in instance.import_order_status_ids:
                instance.last_synced_order_date = before_date
                if before_date and after_date:
                    response = wcapi.get('orders?after=%s&before=%s&status=%s&per_page=100'%(after_date,before_date,order_status.status))
                else:
                    response = wcapi.get('orders?status=%s&per_page=100'%(order_status.status))
                if not isinstance(response,requests.models.Response):                
                    transaction_log_obj.create({'message': "Import Orders \nResponse is not in proper format :: %s"%(response),
                                                 'mismatch_details':True,
                                                 'type':'sales',
                                                 'woo_instance_id':instance.id
                                                })
                    continue                                    
                if response.status_code not in [200,201]:
                    message = "Error in Import Orders %s"%(response.content)                        
                    transaction_log_obj.create(
                                        {'message':message,
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
                    continue
                try:
                    order_ids = order_ids + response.json()
                except Exception as e:
                    transaction_log_obj.create({'message':"Json Error : While import Orders from WooCommerce for instance %s. \n%s"%(instance.name,e),
                                 'mismatch_details':True,
                                 'type':'sales',
                                 'woo_instance_id':instance.id
                                })
                    continue
                total_pages = response.headers.get('x-wp-totalpages')
                if int(total_pages) >=2:
                    for page in range(2,int(total_pages)+1):            
                        order_ids = order_ids + self.import_all_woo_orders(wcapi,instance,transaction_log_obj,order_status,page,after_date,before_date,is_cron)            
            
            import_order_ids=[]
            
            for order in order_ids:
                tax_included  = order.get('prices_include_tax')
                if self.search([('woo_instance_id','=',instance.id),('woo_order_id','=',order.get('id')),('woo_order_number','=',order.get('number'))]):
                    continue
                lines=order.get('line_items')
                if self.check_woo_mismatch_details(lines,instance,order.get('number')):
                    continue
                financial_status = 'paid'
                if order.get('transaction_id'):
                    financial_status = 'paid'
                elif order.get('date_paid') and order.get('payment_method') != 'cod' and order.get('status')=='processing':
                    financial_status = 'paid'
                else:
                    financial_status = 'not_paid'
                
                no_payment_gateway = False
                payment_gateway=self.create_or_update_payment_gateway(instance, order)
                
                if not payment_gateway:
                    no_payment_gateway = self.verify_order(instance,order)
                    if not no_payment_gateway:
                        message="Payment Gateway not found for this order %s and financial status is %s"%(order.get('number'),financial_status)
                        log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                        if not log:
                            transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'sales',
                                                 'woo_instance_id':instance.id
                                                })  
                        continue
                
                workflow = False
                if not no_payment_gateway and payment_gateway:
                    workflow_config=self.env['woo.sale.auto.workflow.configuration'].search([('woo_instance_id','=',instance.id),('financial_status','=',financial_status),('payment_gateway_id','=',payment_gateway.id)],limit=1)
                    workflow=workflow_config and workflow_config.auto_workflow_id or False
    
                if not workflow and not no_payment_gateway:                    
                    message="Workflow Configuration not found for this order %s, financial status is %s and Payment Gateway is %s"%(order.get('number'),financial_status,order.get('payment_method'))
                    log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                    if not log:
                        transaction_log_obj.create(
                                            {'message':message,
                                             'mismatch_details':True,
                                             'type':'sales','woo_instance_id':instance.id
                                            })                    
                    continue
                woo_customer_id = order.get('customer_id',False)
                partner=order.get('billing',False) and self.create_or_update_woo_customer(woo_customer_id,order.get('billing'), False, False,False,instance)
                if not partner:                    
                    message="Customer Not Available In %s Order"%(order.get('number'))
                    log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                    if not log:
                        transaction_log_obj.create(
                                                    {'message':message,
                                                     'mismatch_details':True,
                                                     'type':'sales',
                                                     'woo_instance_id':instance.id
                                                    })
                    continue
                shipping_address=order.get('shipping',False) and self.create_or_update_woo_customer(False,order.get('shipping'), False,partner.id,'delivery',instance) or partner                                                
                new_record = self.new({'partner_id':partner.id})
                new_record.onchange_partner_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})
                new_record = self.new(retval)
                new_record.onchange_partner_shipping_id()
                retval = self._convert_to_write({name: new_record[name] for name in new_record._cache})
                
                fiscal_position=partner.property_account_position_id 
                pricelist_id=retval.get('pricelist_id',False)
                payment_term=retval.get('payment_term_id',False)
                woo_order_vals=self.get_woo_order_vals(order,workflow, partner, instance, partner, shipping_address, pricelist_id, fiscal_position, payment_term, payment_gateway)
                sale_order = self.create(woo_order_vals) if woo_order_vals else False
                
                if not sale_order:
                    continue
#                 sale_order.onchange_partner_id()
#                 sale_order.onchange_partner_shipping_id()
                if not fiscal_position:
                    sale_order.write({'fiscal_position_id':False})
                if tax_included:                                           
                    total_discount=float(order.get('discount_total',0.0)) + float(order.get('discount_tax',0.0))
                if not tax_included:
                    total_discount=float(order.get('discount_total',0.0))                                                                      
                
                import_order_ids.append(sale_order.id)                
                shipping_taxable = False
                tax_datas = []
                tax_ids = []
                for tax_line in order.get('tax_lines'):                    
                    rate_id = tax_line.get('rate_id')
                    if rate_id:
                        res_rate = wcapi.get('taxes/%s'%(rate_id))
                        try:
                            rate = res_rate.json()
                        except Exception as e:
                            transaction_log_obj.create({'message':"Json Error : While retrive Product tax id %s from WooCommerce for instance %s. \n%s"%(rate_id,instance.name,e),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
                            continue                        
                        tax_datas.append(rate)
                        shipping_taxable = rate.get('shipping')                       
                tax_ids = self.get_woo_tax_id_ept(instance,tax_datas,tax_included)
                product=False
                for line in lines:                    
                    woo_product=self.create_or_update_woo_product(line,instance,wcapi)
                    if not woo_product:
                        continue
                    product_url = woo_product and woo_product.producturl or False
                    if product_url:
                        line.update({'product_url':product_url})
                    product=woo_product.product_id
                    actual_unit_price = 0.0                    
                    if tax_included:
                        actual_unit_price=(float(line.get('subtotal_tax')) + float(line.get('subtotal'))) / float(line.get('quantity'))                            
                    else:
                        actual_unit_price = float(line.get('subtotal')) / float(line.get('quantity'))
                    taxes=[]
                    for tax in line.get('taxes'):
                        res_rate = wcapi.get('taxes/%s'%(tax.get('id')))
                        try:
                            rate = res_rate.json()
                        except Exception as e:
                            transaction_log_obj.create({'message':"Json Error : While retrive Product tax id %s from WooCommerce for instance %s. \n%s"%(rate_id,instance.name,e),
                                         'mismatch_details':True,
                                         'type':'sales',
                                         'woo_instance_id':instance.id
                                        })
                            continue
                        tax_rate=float(rate.get('rate',0.0))
                        account_tax=self.env['account.tax'].search([('price_include','=',tax_included),('type_tax_use', '=', 'sale'), ('amount', '=', tax_rate),('company_id','=',instance.warehouse_id.company_id.id)],limit=1)
                        account_tax and taxes.append(account_tax.id)
                    self.create_woo_sale_order_line(line,[(6,0,taxes)],product,line.get('quantity'),fiscal_position,partner,sale_order.pricelist_id.id,product.name,sale_order,actual_unit_price,False)                  
    
                shipping_tax_ids = []                     
                product_template_obj=self.env['product.template']
                for line in order.get('shipping_lines',[]):
                    if shipping_taxable and float(order.get('shipping_tax')) > 0.0:                        
                        shipping_tax_ids =  self.get_woo_tax_id_ept(instance,tax_datas,False)
                    else:
                        shipping_tax_ids = []
                    product=False    
                    delivery_method=line.get('method_title')
                    if delivery_method:
                        carrier=self.env['delivery.carrier'].search([('woo_code','=',delivery_method)],limit=1)
                        if not carrier:
                            carrier=self.env['delivery.carrier'].search([('name','=',delivery_method)],limit=1)
                        if not carrier:
                            carrier=self.env['delivery.carrier'].search(['|',('name','ilike',delivery_method),('woo_code','ilike',delivery_method)],limit=1)
                        if not carrier:
                            product_template=product_template_obj.search([('name','=',delivery_method),('type','=','service')],limit=1)
                            if not product_template:
                                product_template=product_template_obj.create({'name':delivery_method,'type':'service'})
                            carrier=self.env['delivery.carrier'].create({'name':delivery_method,'woo_code':delivery_method,'fixed_price':line.get('total'),'product_id':product_template.product_variant_ids[0].id})
                        sale_order.write({'carrier_id':carrier.id})
                        if carrier.product_id:
                            shipping_product=carrier.product_id
                    line=self.create_woo_sale_order_line(line,shipping_tax_ids,shipping_product,1,fiscal_position,partner,sale_order.pricelist_id.id,shipping_product and shipping_product.name or line.get('method_title'),sale_order,line.get('total'),True)
                if total_discount > 0.0:                                                                                                                            
                    self.create_woo_sale_order_line({},tax_ids,instance.discount_product_id,1,fiscal_position,partner,sale_order.pricelist_id.id,instance.discount_product_id.name,sale_order,total_discount*-1,False)
            
                fee_lines = order.get("fee_lines",[])
                for fee_line in fee_lines:
                    fee_value = fee_line.get("total")
                    fee = fee_line.get("name")
                    fee_line_tax_ids = []
                    fee_line_tax_ids =  self.get_woo_tax_id_ept(instance,tax_datas,False)
                    if fee_value:
                        self.create_woo_sale_order_line({},fee_line_tax_ids,instance.fee_line_id,1,fiscal_position,partner,pricelist_id,fee,sale_order,fee_value,False)
            if import_order_ids:
                self.env['sale.workflow.process.ept'].auto_workflow_process(ids=import_order_ids)
                odoo_orders=self.browse(import_order_ids)
                for order in odoo_orders:
                    order.invoice_shipping_on_delivery=False
        return True    

    @api.model
    def auto_update_woo_order_status_ept(self,ctx={}):
        woo_instance_obj=self.env['woo.instance.ept']
        if not isinstance(ctx,dict) or not 'woo_instance_id' in ctx:
            return True        
        woo_instance_id = ctx.get('woo_instance_id',False)
        if woo_instance_id:
            instance=woo_instance_obj.search([('id','=',woo_instance_id),('state','=','confirmed')])
            instance and self.update_woo_order_status(instance)
        return True
    
    @api.model
    def update_woo_order_status(self,instance):
        transaction_log_obj=self.env["woo.transaction.log"]
        instances=[]
        if not instance:
            instances=self.env['woo.instance.ept'].search([('order_auto_update','=',True),('state','=','confirmed')])
        else:
            instances.append(instance)
        for instance in instances:
            wcapi = instance.connect_in_woo()
            sales_orders = self.search([('warehouse_id','=',instance.warehouse_id.id),
                                        ('woo_order_id','!=',False),
                                        ('woo_instance_id','=',instance.id)
                                        ],order='date_order')

            for sale_order in sales_orders:
                if sale_order.updated_in_woo == True:
                    continue
                for picking in sale_order.picking_ids:
                    """Here We Take only done picking and  updated in woo false"""
                    if picking.updated_in_woo or picking.state!='done' or picking.picking_type_code != 'outgoing':
                        continue                    
                    info = {"status": "completed"}
                    data = info
                    if instance.woo_version == 'old':                    
                        data = {"order":info}
                        response = wcapi.put('orders/%s'%(sale_order.woo_order_id),data)
                    else:
                        data.update({"id":sale_order.woo_order_id})
                        response = wcapi.post('orders/batch',{'update':[data]})
                    if not isinstance(response,requests.models.Response):
                        message = "Update Orders %s Status \nResponse is not in proper format :: %s"%(sale_order.name,response)
                        log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                        if not log:               
                            transaction_log_obj.create({'message': message,
                                                         'mismatch_details':True,
                                                         'type':'sales',
                                                         'woo_instance_id':instance.id
                                                        })
                            continue
                    if response.status_code not in [200,201]:
                        message = "Error in update order %s status,  %s"%(sale_order.name,response.content)
                        log=transaction_log_obj.search([('woo_instance_id','=',instance.id),('message','=',message)])
                        if not log:
                            transaction_log_obj.create(
                                                {'message':message,
                                                 'mismatch_details':True,
                                                 'type':'sales',
                                                 'woo_instance_id':instance.id
                                                })
                            continue
                    try:
                        result = response.json()
                    except Exception as e:
                        transaction_log_obj.create({'message':"Json Error : While update Orders status for order no. %s to WooCommerce for instance %s. \n%s"%(sale_order.woo_order_id,instance.name,e),
                                     'mismatch_details':True,
                                     'type':'sales',
                                     'woo_instance_id':instance.id
                                    })
                        continue
                    if instance.woo_version == 'old':
                        errors = result.get('errors','')
                        if errors:
                            message = errors[0].get('message')
                            transaction_log_obj.create(
                                                        {'message':"Error in update order status,  %s"%(message),
                                                         'mismatch_details':True,
                                                         'type':'sales',
                                                         'woo_instance_id':instance.id
                                                        })
                            continue
                        else:
                            picking.write({'updated_in_woo':True})
                    elif instance.woo_version == 'new':
                        picking.write({'updated_in_woo':True})
        return True
    
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        result=super(sale_order,self).onchange_partner_id()
        return result

class sale_order_line(models.Model):
    _inherit="sale.order.line"
    
    woo_line_id=fields.Char("woo Line")
    
class import_order_status(models.Model):
    _name="import.order.status"
    _description="Order Status"
    
    name=fields.Char("Name")
    status=fields.Char("Status")    
