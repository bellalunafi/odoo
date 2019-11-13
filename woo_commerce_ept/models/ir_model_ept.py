#!/usr/bin/python3
# -*- coding: utf-8 -*-

ept_apps=['woo_commerce_v11','woo_commerce_v11_win','ebay_ept_v11','shopify_ept_v11','amazon_ept_v11','amazon_fba_ept_v11']

import logging

from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

MODULE_UNINSTALL_FLAG = '_force_unlink'


class IrModelDataEpt(models.Model):
    """
        Holds external identifier keys for records in the database.
        This has two main uses:
           * allows easy data integration with third-party systems,
             making import/export/sync of data possible, as records
             can be uniquely identified across multiple systems
           * allows tracking the origin of data installed by Odoo
             modules themselves, thus making it possible to later
             update them seamlessly.
        @author: Vora Mayur
    """
    _inherit = 'ir.model.data'
    
    @api.model
    def _module_data_uninstall(self, modules_to_remove):
        """
            Deletes all the records referenced by the ir.model.data entries
            ``ids`` along with their corresponding database backed (including
            dropping tables, columns, FKs, etc, as long as there is no other
            ir.model.data entry holding a reference to them (which indicates that
            they are still owned by another module). 
            Attempts to perform the deletion in an appropriate order to maximize
            the chance of gracefully deleting all records.
            This step is performed as part of the full uninstallation of a module.
            @author: Vora Mayur
        """ 
        
        if not isinstance(modules_to_remove, list):
            modules_to_remove = [modules_to_remove]
        flag=False
        for custom_module_name in modules_to_remove:
            if custom_module_name in ept_apps:
                flag=True
                break
        if flag:
            if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
                raise AccessError(_('Administrator access is required to uninstall a module'))
    
            # enable model/field deletion
            self = self.with_context(**{MODULE_UNINSTALL_FLAG: True})
    
            datas = self.search([('module', 'in', modules_to_remove)])
            to_unlink = tools.OrderedSet()
            undeletable = self.browse([])
    
            for data in datas.sorted(key='id', reverse=True):
                model = data.model
                res_id = data.res_id
                to_unlink.add((model, res_id))
    
            def unlink_if_refcount(to_unlink):
                undeletable = self.browse()
                for model, res_id in to_unlink:
                    external_ids = self.search([('model', '=', model), ('res_id', '=', res_id)])
                    if external_ids - datas:
                        # if other modules have defined this record, we must not delete it
                        continue
                    if model == 'ir.model.fields':
                        # Don't remove the LOG_ACCESS_COLUMNS unless _log_access
                        # has been turned off on the model.
                        field = self.env[model].browse(res_id).with_context(
                            prefetch_fields=False,
                        )
                        if not field.exists():
                            _logger.info('Deleting orphan external_ids %s', external_ids)
                            external_ids.unlink()
                            continue
                        if field.name in models.LOG_ACCESS_COLUMNS and field.model in self.env and self.env[field.model]._log_access:
                            continue
                        if field.name == 'id':
                            continue
                    _logger.info('Deleting %s@%s', res_id, model)
                    try:
                        self._cr.execute('SAVEPOINT record_unlink_save')
                        self.env[model].browse(res_id).unlink()
                    except Exception:
                        _logger.info('Unable to delete %s@%s', res_id, model, exc_info=True)
                        undeletable += external_ids
                        self._cr.execute('ROLLBACK TO SAVEPOINT record_unlink_save')
                    else:
                        self._cr.execute('RELEASE SAVEPOINT record_unlink_save')
                return undeletable
    
            # Remove non-model records first, then model fields, and finish with models
            # i.e ir.ui.view, ir.model.data, ir.field, ir.actions.act_window, ir.actions.act_window.view, ir.ui.menu, ir.model.access, ir.model, ir.cron    
            undeletable += unlink_if_refcount(item for item in to_unlink if item[0] not in ('ir.model', 'ir.model.fields', 'ir.model.constraint'))
            
            # Remove the constraints of ir.model.constraints
            # Skip This Step
            #undeletable += unlink_if_refcount(item for item in to_unlink if item[0] == 'ir.model.constraint')
    
            # Remove Constraints
            # Skip This Step
            #modules = self.env['ir.module.module'].search([('name', 'in', modules_to_remove)])
            #constraints = self.env['ir.model.constraint'].search([('module', 'in', modules.ids)])
            #constraints._module_data_uninstall()
    
            # Remove the model field or ir.model.fields
            #undeletable += unlink_if_refcount(item for item in to_unlink if item[0] == 'ir.model.fields')
    
            # Remove Model Relations of modules.ids
            # i.e M2O,O2M...etc
            #relations = self.env['ir.model.relation'].search([('module', 'in', modules.ids)])
            #relations._module_data_uninstall()
            
            # Remove Model of ir.model
            #undeletable += unlink_if_refcount(item for item in to_unlink if item[0] == 'ir.model')
    
            (datas - undeletable).unlink()

        else:
            return super(IrModelDataEpt,self)._module_data_uninstall(modules_to_remove)
                