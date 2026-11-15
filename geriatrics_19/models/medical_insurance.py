from odoo import models, fields


class MedicalInsurance(models.Model):
    _name = 'medical.insurance'
    _description = 'Osiguranje pacijenta'
    _order = 'id desc'

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
        domain=[('is_company', '=', True)],
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
            ('penzioner', 'Penzioner'),
            ('centar_soc_rad', 'Centar za socijalni rad'),
            ('suprug', 'Preko supružnika'),
            ('poljuprivredno', 'Poljoprivredno'),
            ('zavod', 'Zavod'),
            ('radni', 'Radni odnos'),
            ('dobrovoljno', 'Dobrovoljno'),
            ('izbjegli', 'Izbjeglički status'),
        ],
        string='Vrsta osiguranja',
    )

    notes = fields.Text(
        string='Napomene',
    )
