from odoo import models, fields, api

class MedicalPatient(models.Model):
    _name = 'medical.patient'
    _description = 'Pacijent'

    patient_number = fields.Char(
        string='Broj pacijenta',
        required=True,
        index=True,
    )

    jmbg = fields.Char(
        string='JMBG',
        groups='geriatrics_19.group_patient_sensitive_data',
        copy=False,
    )

    legacy_id = fields.Integer(
        string='Odoo 8 ID pacijenta',
        index=True,
        copy=False,
    )

    id_number = fields.Char(
        string='Broj licnog dokumenta',
        groups='geriatrics_19.group_patient_sensitive_data',
    )

    active = fields.Boolean(
        string='Aktivan',
        default=True,
    )
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Kontakt', 
        required=True, 
        ondelete='restrict'
    )
    _unique_partner = models.Constraint(
        'UNIQUE(partner_id)',
        'Ovaj kontakt je već registrovan kao pacijent.'
    )
