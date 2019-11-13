{
    
    # App information
    'name': 'Automatic Workflow Settings',
    'version': '12.0',
    'category': 'Sale',
   'license': 'OPL-1',
    
    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    
    # Dependencies
    'depends': ['sale_management','account','stock'], 
    
	#View
	'init_xml': [],
    'data': [ 
            'view/sale_workflow_process_view.xml',
            'view/automatic_workflow_data.xml',
            'view/sale_view.xml',
            'view/transaction_log_view.xml',
            'security/ir.model.access.csv',
            'view/stock_move.xml',
            'view/global_channel_ept.xml',
            'view/stock_picking.xml',
            'view/account_invoice.xml',
            'view/account_move.xml',
    ],
    'demo_xml': [],
    
    'installable': True,
    'active': False,
    'images': ['static/description/Automatic-Workflow-Cover.jpg']
}

