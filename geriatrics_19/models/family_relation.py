from odoo import models, fields

class FamilyRelation(models.Model):
    _name = 'geriatrics.family.relation'
    _description = 'Porodična veza'

    partner_id = fields.Many2one(
        'res.partner',
        string='Povezani kontakt',
        ondelete='restrict',
    )

    family_partner_id = fields.Many2one(
        'res.partner',
        string='Član porodice / kontakt osoba',
        required=True,
        ondelete='restrict',
    )

    relationship_type_id = fields.Many2one(
        'geriatrics.relationship.type',
        string='Vrsta srodstva',
        ondelete='restrict',
    )

    note = fields.Text(string='Napomena')

    legacy_relationship = fields.Text(
        string='Originalna vrijednost srodstva',
        copy=False,
    )

    legacy_id = fields.Integer(
        string='ID veze u Odoo 8',
        copy=False,
        index=True,
    )


  