from odoo import models,api


class account_invoice(models.Model):
    _inherit = "account.invoice"
    
    @api.multi
    def account_refund_invoice_ept(self,journal_id,product_ids,invoice_id,date_posted,datas):
        obj_invoice_line = self.env['account.invoice.line']
        invoice_obj = self.browse(invoice_id)
        refund_invoice = invoice_obj.refund(date_posted,date_posted,invoice_obj.name,journal_id)
        refund_invoice.compute_taxes()
        refund_invoice.write({'date_invoice':date_posted,'origin':invoice_obj.name})
        extra_invoice_lines = obj_invoice_line.search([('invoice_id','=',refund_invoice.id),('product_id','not in',product_ids)])
        if extra_invoice_lines:
            extra_invoice_lines.unlink()
        invoice_lines = obj_invoice_line.search([('invoice_id','=',refund_invoice.id),('product_id','=',datas.get('product_id'))])
        exact_line=False
        if len(invoice_lines.ids)>1: 
            exact_line=obj_invoice_line.search([('invoice_id','=',refund_invoice.id),('product_id','=',datas.get('product_id'))],limit=1)
            if exact_line:
                other_lines=obj_invoice_line.search([('invoice_id','=',refund_invoice.id),('product_id','=',datas.get('product_id')),('id','!=',exact_line.id)])  
                other_lines.unlink()
                exact_line.write({'quantity':datas.get('qty'),'price_unit':datas.get('amount')})
        else:
            invoice_lines.write({'quantity':datas.get('qty'),'price_unit':datas.get('amount')})  
            refund_invoice.compute_taxes()
            refund_invoice.action_invoice_open()
    
    @api.multi
    def create_account_invoice_ept(self,vals):
        partner_obj = self.env['res.partner'].browse(vals.get('partner_id'))
        invoice_vals = {
            'type': vals.get('type'),
            'reference': vals.get('ref'),
            'account_id': partner_obj.property_account_receivable_id.id,
            'partner_id': partner_obj.id,
            'journal_id': vals.get('journal_id',''),
            'fiscal_position_id': vals.get('fiscal_position_id',''),
            'company_id':vals.get('company_id',''),
            'user_id': self._uid or False,
            'date_invoice':vals.get('date_invoice')
        }
    
        return invoice_vals
    
    @api.multi
    def create_account_invoice_line_ept(self,vals):
        invoice_line_obj=self.env['account.invoice.line']
        product_obj = self.env['product.product'].browse(vals.get('product_id'))
        invoice_line = {
              'product_id':vals.get('product_id'),
              'name':product_obj.name,
              'invoice_id':vals.get('invoice_id'),
              'price_unit':vals.get('price_unit'),
              'quantity':vals.get('qty') or 1.00,
              'uom_id':product_obj.uom_id.id,
            }
        new_record=invoice_line_obj.new(invoice_line)
        new_record._onchange_product_id()
        new_record = invoice_line_obj._convert_to_write({name: new_record[name] for name in new_record._cache})
        new_record.update({'price_unit':vals.get('price_unit'),'tax_ids':[(6,0,vals.get('tax_ids'))]})
        return new_record
        
        