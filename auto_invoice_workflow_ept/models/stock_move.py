from odoo import models,fields,api


class stock_move(models.Model):
    _inherit = "stock.move"
    
    producturl = fields.Text("Product URL")

    # Added by sagar
    # Pass context for when create accounting entries of the stock move than set the global_channel_id in account_move and account_move_line
    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        ctx = dict(self._context)
        ctx.update({'global_channel_id':self.picking_id.global_channel_id.id})
        return super(stock_move, self.with_context(ctx))._create_account_move_line(credit_account_id, debit_account_id, journal_id)
    