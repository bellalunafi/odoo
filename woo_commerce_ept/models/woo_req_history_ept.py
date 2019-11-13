from odoo import fields,models,api
import pytz
from datetime import datetime

class woo_req_res_ept(models.Model):
    _name='woo.req.history.ept'
    _rec_name='woo_instance_id'
    _order='create_date desc'
    _description = "WooCommerce Debug Details"
    url=fields.Text('URL')
    type=fields.Many2one('woo.req.type.ept',string='Type')
    req=fields.Text('Request')
    res=fields.Text('Response')
    req_time=fields.Char("Request Time",readonly="1")
    res_time=fields.Char("Response Time",readonly="1")
    woo_instance_id=fields.Many2one('woo.instance.ept',string='WooCommerce Instance')
    
    @api.multi
    def req_res_data(self,method,url,verify_ssl,auth,params,data,timeout,headers,res,req_time,res_time):
        woo_instance_obj=self.env['woo.instance.ept']
        woo_req_type_obj=self.env['woo.req.type.ept']
        host = ""
        if url.__contains__('wc-api'):
            host=url.split('wc-api')[0][:-1]
        if url.__contains__('wp-json'):
            host=url.split('wp-json')[0][:-1]
        if host:
            woo_instance=woo_instance_obj.search([('host','=',host)],limit=1)
            if not woo_instance:
                woo_instance=woo_instance_obj.search([('host','=',"%s/"%(host))],limit=1)
        if woo_instance:
            if woo_instance.is_show_debug_info:
                req_type=""
                woo_req_type=False
                if url and url.split("/")[0]=="https:":
                    url="%s?consumer_key=%s&consumer_secret=%s"%(url,params.get('consumer_key'),params.get('consumer_secret'))
                if url and url.__contains__("wc/v1") or url.__contains__("wc/v2"):
                    if url.__contains__("wc/v1"):
                        req_type = url.split("?")[0].split("/v1/")[1].replace("/", " ")
                    if url.__contains__("wc/v2"):
                        req_type = url.split("?")[0].split("/v2/")[1].replace("/", " ")
                    result = ''.join(i for i in req_type if not i.isdigit())
                    if not result[-1].isalpha():
                        result=result[:-1]
                    woo_req_type = woo_req_type_obj.search([('name','=',result.title())],limit=1)
                    if not woo_req_type:
                        woo_req_type = woo_req_type_obj.create({'name':result.title()})
                if url and url.__contains__("wc-api/v3"):
                    req_type = url.split("?")[0].split("/wc-api/v3/")[1].replace("/", " ")
                    result = ''.join(i for i in req_type if not i.isdigit())
                    if not result[-1].isalpha():
                        result=result[:-1]
                    woo_req_type = woo_req_type_obj.search([('name','=',result.title())],limit=1)
                    if not woo_req_type:
                        woo_req_type = woo_req_type_obj.create({'name':result.title()})
                if self._context.get('tz'):
                    tz = pytz.timezone(self._context.get('tz'))
                    req_time = pytz.utc.localize(datetime.strptime(req_time,"%d/%m/%Y %H:%M:%S.%f")).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S.%f") 
                    res_time = pytz.utc.localize(datetime.strptime(res_time,"%d/%m/%Y %H:%M:%S.%f")).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S.%f")      
                vals={
                    'url':url,
                    'req':data,
                    'type':woo_req_type and woo_req_type.id or '',
                    'res':res.content and res.content,
                    'woo_instance_id':woo_instance.id,
                    'req_time':req_time,
                    'res_time':res_time
                    }
                self.create(vals)