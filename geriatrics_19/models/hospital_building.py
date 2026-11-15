from odoo import fields, models


class MedicalHospitalBuilding(models.Model):
    _name = 'medical.hospital.building'
    _description = 'Objekat zdravstvene ustanove'
    _order = 'name'

    legacy_id = fields.Integer(
        string='Originalni Odoo 8 ID',
        index=True,
        copy=False,
        readonly=True,
    )

    _legacy_id_unique_index = models.UniqueIndex(
        '(legacy_id) WHERE legacy_id > 0',
        'Originalni Odoo 8 ID mora biti jedinstven.',
    )

    name = fields.Char(
        string='Naziv objekta',
        required=True,
    )

    institution_id = fields.Many2one(
        'res.partner',
        domain=[('is_company', '=', True)],
        string='Ustanova',
        ondelete='restrict',
    )

    code = fields.Char(
        string='Šifra objekta',
    )

    extra_info = fields.Text(
        string='Dodatne informacije',
    )
