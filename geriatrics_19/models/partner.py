from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    patient_id = fields.One2many(
        'medical.patient',
        'partner_id',
        string='Pacijent',
    )
