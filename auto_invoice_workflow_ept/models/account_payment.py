from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    #set the global_channel_id from accout_invoice to respected payment
    def _create_payment_entry(self, amount):
        res = super(AccountPayment, self)._create_payment_entry(amount)
        invoice_id = False
        if self._context.get('active_model') == 'account.invoice':
            invoice_id = self.env['account.invoice'].browse(self._context.get('active_id'))
            for move in res:
                move.global_channel_id = invoice_id.global_channel_id.id if invoice_id else False
                for line in move.line_ids:
                    line.global_channel_id = invoice_id.global_channel_id.id if invoice_id else False
        return res