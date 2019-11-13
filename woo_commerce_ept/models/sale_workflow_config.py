from odoo import models,fields

class woo_sale_auto_workflow_configuration(models.Model):
    _name="woo.sale.auto.workflow.configuration"
    _description = "Financial Status"
    
    financial_status=fields.Selection([('paid','The finances have been paid'),
                                        ('not_paid','The finances have been not paid'),                                        
                                        ],default="paid",required=1)
    auto_workflow_id=fields.Many2one("sale.workflow.process.ept","Auto Workflow",required=1)
    
    woo_instance_id=fields.Many2one("woo.instance.ept","Instance",required=1)
    payment_gateway_id=fields.Many2one("woo.payment.gateway","Payment Gateway",required=1)

    _sql_constraints=[('_workflow_unique_constraint','unique(financial_status,woo_instance_id,payment_gateway_id)','Financial status must be unique in the list')]
    
    