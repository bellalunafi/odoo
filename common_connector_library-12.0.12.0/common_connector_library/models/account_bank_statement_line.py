from odoo import models,api

class account_bank_statement_line(models.Model):
    _inherit = "account.bank.statement.line"
    
    @api.model
    def convert_move_amount_currency(self,bank_statement,moveline,amount):
        amount_currency = 0.0
        if moveline.company_id.currency_id.id != bank_statement.currency_id.id:
            amount_currency = moveline.currency_id.compute(moveline.amount_currency,bank_statement.currency_id)            
        elif (moveline.invoice_id and moveline.invoice_id.currency_id.id != bank_statement.currency_id.id):                            
            amount_currency = moveline.invoice_id.currency_id.compute(amount,bank_statement.currency_id)
        currency = moveline.currency_id.id
        return currency,  amount_currency
    
    @api.multi
    def statement_line_changes_reconcile(self,statement_line,account_id,tax_ids=[]):
        bank_statement_line = self.browse(statement_line)
        #account_id = bank_statement_line.account_id.id
        mv_dicts = {
                    'account_id':account_id,
                    'debit': bank_statement_line.amount < 0 and -bank_statement_line.amount or 0.0,
                    'credit': bank_statement_line.amount > 0 and bank_statement_line.amount or 0.0,
                    'tax_ids':[(6,0,tax_ids)] or []
                    }
        bank_statement_line.process_reconciliation(new_aml_dicts=[mv_dicts])
        return True
    
    @api.multi
    def reconcile_order_invoices_transaction(self,sale_order,invoice_type,statement_line):
        statement_line_obj=self.env['account.bank.statement.line']
        move_line_obj = self.env['account.move.line']
        invoice_obj=self.env['account.invoice']
        sale_order_obj=self.env['sale.order']
        line_obj = statement_line_obj.browse(statement_line)
        bank_statement = line_obj.statement_id.id
        so_obj = sale_order_obj.browse(sale_order)
        invoices = invoice_obj.browse()
        invoices += so_obj.invoice_ids
        invoices = invoices.filtered(lambda record: record.type == invoice_type and record.state in ['open'])
        account_move_ids = list(map(lambda x:x.move_id.id,invoices))
        move_lines = move_line_obj.search([('move_id','in',account_move_ids),
                                           ('user_type_id.type','=','receivable'),
                                           ('reconciled','=',False)])
        mv_line_dicts = []
        move_line_total_amount = 0.0
        currency_ids = []
        for moveline in move_lines:
            amount = moveline.debit - moveline.credit
            amount_currency = 0.0
            if moveline.amount_currency:
                currency,amount_currency = self.convert_move_amount_currency(bank_statement,moveline,amount)
                if currency:
                    currency_ids.append(currency)
            if amount_currency:
                amount = amount_currency
            mv_line_dicts.append({
                                  'credit':abs(amount) if amount >0.0 else 0.0,
                                  'name':moveline.invoice_id.number,
                                  'move_line':moveline,
                                  'debit':abs(amount) if amount < 0.0 else 0.0
                                  })
            move_line_total_amount += amount
        if round(line_obj.amount,10) == round(move_line_total_amount,10) and (not line_obj.currency_id or  line_obj.currency_id.id==bank_statement.currency.id):
            if currency_ids:
                currency_ids = list(set(currency_ids))
                if len(currency_ids)==1:
                    statement_line.write({'amount_currency':move_line_total_amount,'currency_id':currency_ids[0]})
            line_obj.process_reconciliation(mv_line_dicts)
            