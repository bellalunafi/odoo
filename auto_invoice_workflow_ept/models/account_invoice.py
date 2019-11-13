from odoo import models, fields, api, _

class global_channel(models.Model):
    _inherit = "account.invoice"
    
    global_channel_id=fields.Many2one('global.channel.ept' ,string='Global Channel')
    
    @api.multi
    def action_move_create(self):
        result=super(global_channel,self).action_move_create()
        for record in self : 
            record.move_id.global_channel_id  = record.global_channel_id
            for line in record.move_id.line_ids:
                line.global_channel_id=record.global_channel_id.id
            
        return result

    @api.multi
    def _write(self, vals):
        res = super(global_channel, self)._write(vals)
        if self._context.get('account_bank_statement_line_id',False):
            statement_line = self.env['account.bank.statement.line'].browse(self._context.get('account_bank_statement_line_id'))
            for line in statement_line:
                for move_line in line.journal_entry_ids:
                    move_line.move_id.global_channel_id = self.global_channel_id.id
                    for line1 in move_line.move_id.line_ids:
                        line1.global_channel_id = self.global_channel_id.id
        return res
