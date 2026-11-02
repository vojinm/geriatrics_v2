from odoo import models, fields

class MedicalPatientTracking(models.Model):
    _name = 'medical.patient.tracking.list'
    _description = 'Evidencija rada s pacijentom'
    _order = 'date desc, id desc'

    patient_id = fields.Many2one(
        'medical.patient',
        string='Pacijent',
        required=True,
        ondelete='cascade',
        index=True,
    )

    date = fields.Date(
        string='Datum aktivnosti',
        required=True,
        default=fields.Date.context_today,
    )

    info = fields.Text(
        string='opis aktivnosti',
        required=True,
    )