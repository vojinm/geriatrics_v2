from odoo import models, fields


class RelationshipType(models.Model):
    _name = 'geriatrics.relationship.type'
    _description = 'Vrsta srodstva'
    _order = 'name'

    name = fields.Char(
        string='Naziv srodstva',
        required=True,
    )

    active = fields.Boolean(
        string='Aktivno',
        default=True,
    )