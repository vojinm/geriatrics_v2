from odoo import models, fields


class MedicalPatientActivity(models.Model):
    _name = 'medical.patient.activities'
    _description = 'Aktivnost pacijenta'
    _order = 'name'

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

    name = fields.Char(
        string='Naziv aktivnosti',
        required=True,
    )

    notes = fields.Text(
        string='Dodatne informacije',
    )
