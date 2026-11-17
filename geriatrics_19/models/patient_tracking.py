from odoo import models, fields, api


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

    evidentirao = fields.Char(
        string='Evidentirao',
        compute='_compute_evidentirao',
        store=False,
        readonly=True,
    )

    @api.depends('legacy_id', 'legacy_create_uid', 'create_uid', 'create_uid.name')
    def _compute_evidentirao(self):
        legacy_users = {
            1: 'B++',
            5: 'Ljiljana Marjanović',
            12: 'Predrag Dragičević',
            13: 'Vladimir Miljković',
            19: 'Renata Ražić',
            20: 'Mirjana Janković',
            21: 'Darinka Mandić',
        }

        for record in self:
            if record.legacy_id and record.legacy_create_uid:
                record.evidentirao = legacy_users.get(
                    record.legacy_create_uid,
                    f'Odoo 8 korisnik #{record.legacy_create_uid}',
                )
            else:
                record.evidentirao = record.create_uid.name or ''