from odoo import models, fields, api, _

class global_channel(models.Model):
    _inherit = "account.move.line"
    
    global_channel_id=fields.Many2one('global.channel.ept' ,string='Global Channel')

    # Set the global_channel_id from account_bank_statement_line
    @api.multi
    def create(self,vals):
        res = super(global_channel, self).create(vals)
        if self._context.get('account_bank_statement_line_id'):
            if self._context.get('account_bank_statement_line_id') == vals.get('statement_line_id',False):
                global_channel_id = []
                for line in res.move_id.line_ids:
                    if line.global_channel_id:
                        global_channel_id.append(line.global_channel_id.id)
                if global_channel_id:
                    res.global_channel_id = global_channel_id[0]
        return res