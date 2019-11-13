from odoo import models,api

class res_partner(models.Model):
    _inherit = "res.partner"
       
    @api.multi
    def _prepare_partner_vals(self, vals):
        """
            This function prepare dictionary for the res.partner.
            @note: You need to prepare partner values and pass as dictionary in this function.
            @requires: name
            @param vals: {'name': 'emipro', 'street': 'address', 'street2': 'address', 'email': 'test@test.com'...}
            @return: values of partner as dictionary
        """
        context = dict(self._context)
        state_code = vals.get('state_code','')
        state_name = vals.get('state_name','')
        country_code = vals.get('country_code','')
        country_name = vals.get('country_name','')
        country_obj = self.env['res.country'].search(['|',('code','=',country_code),('name','=',country_name)],limit=1)
        
        state_obj = self.env['res.country.state'].search(['|',('name','=',state_name),('code','=',state_code),('country_id','=',country_obj.id)],limit=1)
        if context.get('create_new_state',False) and not state_obj and state_name:
            state_obj = self.create({'country_id': country_obj.id, 'name': state_name,'code': context.get('new_state_code','')}) if context.get('new_state_code',False) else self.create({'country_id':country_obj.id, 'name': state_name,'code': state_code}) 
        
        partner_vals = {
            'name': vals.get('name'),
            'parent_id':vals.get('parent_id',False),
            'street': vals.get('street',''),
            'street2': vals.get('street2',''),
            'city': vals.get('city',''),
            'state_id': state_obj and state_obj.id or False,
            'country_id': country_obj and country_obj.id or False,
            'phone': vals.get('phone',''),
            'email': vals.get('email'),
            'zip': vals.get('zip',''),
            'lang': vals.get('lang',False),
            'company_id': vals.get('company_id',False),
            'type': vals.get('type',False),
            'is_company': vals.get('is_company',False),
        }
        if context.get('return_with_state_and_country_obj',False):
            return partner_vals, country_obj, state_obj
        return partner_vals
        
    def _find_partner(self, vals, key_list=[], extra_domain=[]):
        """
            This function find the partner based on domain. 
            This function map the keys of the key_list with the dictionary and create domain and if you have give the extra_domain so 
                it will merge with _domain (i.e _domain = _domain + extra_domain).
            @requires: vals, key_list
            @param vals: i.e {'name': 'emipro', 'street': 'address', 'street2': 'address', 'email': 'test@test.com'...}
            @param key_list: i.e ['name', 'street', 'street2', 'email',...]
            @param extra_domain: This domain for you can pass your own custom domain. i.e [('name', '!=', 'test')...]   
            @return: partner object or False
        """
        if key_list and vals:
            _domain = [] + extra_domain
            for key in key_list:
                if not vals.get(key,False):
                    continue
                (key in vals) and _domain.append((key,'=',vals.get(key)))
            return _domain and self.search(_domain,limit=1) or False
        return False