from odoo import models, fields, api, _

class global_channel(models.Model):
    _inherit = "account.move"
    
    global_channel_id=fields.Many2one('global.channel.ept', string='Global Channel')

    # set global_channel_id from the stock move and picking
    @api.model
    def create(self, vals):
        res = super(global_channel, self).create(vals)
        if vals.get('stock_move_id',False) and self._context.get('global_channel_id',False):
            res.write({'global_channel_id':self._context.get('global_channel_id')})
            for line in res.line_ids:
                line.write({'global_channel_id':self._context.get('global_channel_id')})
        return res