from odoo import models, fields


class MedicalPatientTracking(models.Model):
    _name = 'medical.patient.tracking.list'
    _description = 'Evidencija rada s pacijentom'
    _order = 'date desc, id desc'

    legacy_id = fields.Integer(
        string='Originalni Odoo 8 ID',
        index=True,
        copy=False,
        readonly=True,
    )

    _legacy_id_unique_index = models.UniqueIndex(
        "(legacy_id) WHERE legacy_id > 0",
        "Originalni Odoo 8 ID mora biti jedinstven.",
    )

    legacy_create_uid = fields.Integer(
        string='Originalni autor (Odoo 8)',
        readonly=True,
        copy=False,
    )

    legacy_write_uid = fields.Integer(
        string='Originalni urednik (Odoo 8)',
        readonly=True,
        copy=False,
    )

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
        string='Opis aktivnosti',
        required=False,
    )
