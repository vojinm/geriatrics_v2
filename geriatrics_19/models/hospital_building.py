from odoo import fields, models


class MedicalHospitalBuilding(models.Model):
    _name = 'medical.hospital.building'
    _description = 'Objekat zdravstvene ustanove'
    _order = 'name'

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
