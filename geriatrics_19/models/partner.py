from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    patient_id = fields.One2many(
        'medical.patient',
        'partner_id',
        string='Pacijent',
    )

    birthdate = fields.Date(
        string='Datum rođenja',
    )

    lastname = fields.Char(
        string='Prezime',
    )

    sex = fields.Selection(
        selection=[
            ('male', 'Muško'), 
            ('female', 'Žensko')
        ],
        string='Pol',
    )
    
