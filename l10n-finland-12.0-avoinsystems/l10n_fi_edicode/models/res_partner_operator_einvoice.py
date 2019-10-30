from odoo import fields, models, api
from odoo.osv import expression


class ResPartnerOperatorEinvoice(models.Model):
    _name = 'res.partner.operator.einvoice'
    _description = 'Adds operator name and identifier fields'

    name = fields.Char(
        string='Operator',
        required=True,
    )
    identifier = fields.Char(
        string='Identifier',
        required=True,
    )

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('identifier', '=ilike', name + '%'),
                      ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        operators = self.search(domain + args, limit=limit)
        return operators.name_get()
