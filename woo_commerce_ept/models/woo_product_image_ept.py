from odoo import models, fields, api
import base64
import requests

class woo_product_image_ept(models.Model):
    _name = 'woo.product.image.ept'
    _rec_name = "sequence"
    _order='sequence'
    _description = "WooCommerce Gallery Image"

    @api.one
    def set_image(self):
        for product_image in self:
            if product_image.woo_instance_id.is_image_url:
                if product_image.response_url:
                    try:  
                        img = requests.get(product_image.response_url,stream=True,verify=False,timeout=10)
                        if img.status_code == 200:
                            product_image.url_image_id=base64.b64encode(img.content)
                        else:
                            img = requests.get(product_image.url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:
                                product_image.url_image_id=base64.b64encode(img.content)
                    except Exception:
                        try:  
                            img = requests.get(product_image.url,stream=True,verify=False,timeout=10)
                            if img.status_code == 200:
                                product_image.url_image_id=base64.b64encode(img.content)
                        except Exception:
                            pass
                
                elif product_image.url:          
                    try:  
                        img = requests.get(product_image.url,stream=True,verify=False,timeout=10)
                        if img.status_code == 200:
                            product_image.url_image_id=base64.b64encode(img.content)
                    except Exception:
                        pass

    @api.depends('woo_product_tmpl_id')
    def _set_instance(self):
        for woo_gallery_img in self:
            woo_gallery_img.woo_instance_id = woo_gallery_img.woo_product_tmpl_id.woo_instance_id.id
                    
    sequence = fields.Integer("Sequence",defaule=None)
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",readonly=True,compute="_set_instance",store=True)
    is_image_url=fields.Boolean("Is Image Url?",related="woo_instance_id.is_image_url")
    image=fields.Binary("Image")                       
    woo_product_tmpl_id = fields.Many2one('woo.product.template.ept', string='WooCommerce Product')              
    url = fields.Char(size=600, string='Image URL')
    response_url = fields.Char(size=600, string='Response URL',help="URL from WooCommerce")
    url_image_id=fields.Binary("Image URL ID",compute=set_image,store=False)
    woo_image_id=fields.Integer("Woo Image Id",help="WooCommerce Image Id")
