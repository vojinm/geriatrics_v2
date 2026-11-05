from odoo import models, fields


class MedicalInsurance(models.Model):
    _name = 'medical.insurance'
    _description = 'Osiguranje pacijenta'
    _order = 'id desc'

    name = fields.Many2one(
        'res.partner',
        string='Nosilac osiguranja',
    )

    number = fields.Char(
        string='Broj osiguranja',
        size=64,
    )

    company = fields.Many2one(
        'res.partner',
        string='Osiguravajuća institucija',
    )

    member_since = fields.Date(
        string='Datum početka',
    )

    member_exp = fields.Date(
        string='Datum isteka',
    )

    category = fields.Char(
        string='Kategorija osiguranja',
        size=64,
    )

    type = fields.Selection(
        [
            ('state', 'Državno'),
            ('labour_union', 'Sindikalno'),
            ('private', 'Privatno'),
        ],
        string='Vrsta osiguranja',
    )

    notes = fields.Text(
        string='Napomene',
    )