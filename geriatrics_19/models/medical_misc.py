from odoo import models, fields


class InpatientRequestReason(models.Model):
    _name = 'medical.inpatient.request.reason'
    _description = 'Razlog zahtjeva za hospitalizaciju'

    name = fields.Char(string='Naziv', required=True)
    info = fields.Text(string='Dodatne informacije')


class PatientPensionType(models.Model):
    _name = 'medical.patient.pension.type'
    _description = 'Vrsta penzije pacijenta'

    name = fields.Char(string='Naziv', required=True)
    info = fields.Text(string='Dodatne informacije')


class PatientBodyDeformation(models.Model):
    _name = 'medical.patient.body.deformation'
    _description = 'Tjelesni deformitet'

    name = fields.Char(string='Naziv', required=True)
    info = fields.Text(string='Dodatne informacije')


class PatientMindDeformation(models.Model):
    _name = 'medical.patient.mind.deformation'
    _description = 'Mentalni deformitet'

    name = fields.Char(string='Naziv', required=True)
    info = fields.Text(string='Dodatne informacije')


class MedicalEthnicity(models.Model):
    _name = 'medical.ethnicity'
    _description = 'Etnička grupa'

    name = fields.Char(string='Etnička grupa', required=True, size=128)
    code = fields.Char(string='Šifra', size=64)


class MedicalOccupation(models.Model):
    _name = 'medical.occupation'
    _description = 'Zanimanje'

    name = fields.Char(string='Zanimanje', required=True, size=128)
    code = fields.Char(string='Šifra', size=64)
