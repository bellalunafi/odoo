from odoo import models, fields, api, _

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"


    @api.multi
    def process_reconciliations(self, data):
        ctx = dict(self._context)
        ctx.update({'account_bank_statement_line_id':self.id})
        res = super(AccountBankStatementLine, self.with_context(ctx)).process_reconciliations(data)
        return res

