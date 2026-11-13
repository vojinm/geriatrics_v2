from odoo import fields, models


class MedicalHospitalUnit(models.Model):
    _name = 'medical.hospital.unit'
    _description = 'Odjel ustanove'
    _order = 'name'

    name = fields.Char(
        string='Naziv odjela',
        required=True,
    )

    code = fields.Char(
        string='Šifra odjela',
    )

    institution_id = fields.Many2one(
        'res.partner',
        domain=[('is_company', '=', True)],
        string='Ustanova',
        ondelete='restrict',
    )

    extra_info = fields.Text(
        string='Dodatne informacije',
    )