# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{

	'name': 'Common Connector Library',
	'version': '12.0',
    'category': 'Sale',
    'license': 'OPL-1',
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',

    'description': """
    Develope Generalize Method Of Sale Order,Sale Order Line which is use in any Connector 
    to Create Sale Order and Sale Order Line.
    """,
    'website': 'www.emiprotechnologies.com',
    'depends': ['delivery','sale_stock'],
    
    'data': [
		'view/stock_quant_package_view.xml',   
        ],
    
    
    'installable': True,
    'active': False,
    'price': '20',
    'currency': 'EUR',
    
    
    'images': ['static/description/Common-Connector-Library-Cover.jpg']
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
