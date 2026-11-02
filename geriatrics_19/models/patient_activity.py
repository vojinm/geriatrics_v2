from odoo import models, fields

class MedicalPatientActivity(models.Model):
    _name = 'medical.patient.activities'
    _description = 'Aktivnost pacijenta'
    _order = 'name'

    name = fields.Char(
        string='Naziv aktivnosti',
        required=True,
    )

    notes = fields.Text(
        string='Dodatne informacije',
    )
