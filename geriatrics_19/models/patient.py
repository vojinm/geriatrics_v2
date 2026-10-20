from odoo import models, fields, api

class MedicalPatient(models.Model):
    _name = 'medical.patient'
    _description = 'Pacijent'

    partner_id = fields.Many2one(
        'res.partner', 
        string='Kontakt', 
        required=True, 
        ondelete='restrict'
    )
    _unique_partner = models.Constraint(
        'UNIQUE(partner_id)',
        'Ovaj kontakt je vecć registrovan kao pacijent.'
    )
