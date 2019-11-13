from odoo import models,fields,api


class global_channel(models.Model):
    _name = 'global.channel.ept'
    _description = "Sales Channel"
    
    name=fields.Char("Name")