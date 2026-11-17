from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MedicalPatient(models.Model):
    _name = 'medical.patient'
    _description = 'Pacijent'

    inpatient_ids = fields.One2many(
        'medical.inpatient.registration',
        'patient_id',
        string='Hospitalizacije pacijenta',
    )

    hospitalization_institution_id = fields.Many2one(
        'res.partner',
        string='Trenutna ustanova',
        compute='_compute_hospitalization_unit',
        store=True,
    )

    hospitalization_building_id = fields.Many2one(
        'medical.hospital.building',
        string='Trenutni objekat',
        compute='_compute_hospitalization_unit',
        store=True,
    )

    hospitalization_unit_id = fields.Many2one(
        'medical.hospital.unit',
        string='Aktuelni odjel',
        compute='_compute_hospitalization_unit',
        store=True,
    )

    hospitalization_ward_id = fields.Many2one(
        'medical.hospital.ward',
        string='Trenutna soba',
        compute='_compute_hospitalization_unit',
        store=True,
    )

    hospitalization_bed_id = fields.Many2one(
        'medical.hospital.bed',
        string='Trenutni krevet',
        compute='_compute_hospitalization_unit',
        store=True,
    )

    @api.depends(
        'inpatient_ids.state',
        'inpatient_ids.hospitalization_date',
        'inpatient_ids.medical_hospital_unit_id',
        'inpatient_ids.bed_id',
        'inpatient_ids.patient_id',
        'inpatient_ids.bed_id.ward_id',
        'inpatient_ids.bed_id.ward_id.building_id',
        'inpatient_ids.medical_hospital_unit_id.institution_id',
    )
    def _compute_hospitalization_unit(self):
        for patient in self:
            hospitalizations = patient.inpatient_ids.filtered(
                lambda h: h.state == 'hospitalized'
            )

            hospitalization = hospitalizations.sorted(
                key=lambda h: (h.hospitalization_date or fields.Date.to_date('1900-01-01'), h.id),
                reverse=True,
            )[:1]

            unit = hospitalization.medical_hospital_unit_id
            bed = hospitalization.bed_id
            ward = bed.ward_id
            building = ward.building_id

            patient.hospitalization_institution_id = (
                unit.institution_id or ward.institution_id or False
            )
            patient.hospitalization_building_id = building or False
            patient.hospitalization_unit_id = unit or False
            patient.hospitalization_ward_id = ward or False
            patient.hospitalization_bed_id = bed or False

    inpatient_count = fields.Integer(
        string='Hospitalizacije',
        compute='_compute_inpatient_count',
    )

    def _compute_inpatient_count(self):
        Inpatient = self.env['medical.inpatient.registration']
        for patient in self:
            patient.inpatient_count = Inpatient.search_count([
                ('patient_id', '=', patient.id),
            ])

    def action_view_inpatient(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hospitalizacija',
            'res_model': 'medical.inpatient.registration',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
            },
        }

    tracking_count = fields.Integer(
        string='Praćenje aktivnosti',
        compute='_compute_tracking_count',
    )

    def _compute_tracking_count(self):
        Tracking = self.env['medical.patient.tracking.list']
        for patient in self:
            patient.tracking_count = Tracking.search_count([
                ('patient_id', '=', patient.id),
            ])

    def action_view_tracking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Praćenje aktivnosti',
            'res_model': 'medical.patient.tracking.list',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
            },
        }

    contract_count = fields.Integer(
        string='Ugovori',
        compute='_compute_contract_count',
    )

    def _compute_contract_count(self):
        Contract = self.env['medical.patient.contract']
        for patient in self:
            patient.contract_count = Contract.search_count([
                ('patient_id', '=', patient.id),
            ])

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ugovori pacijenta',
            'res_model': 'medical.patient.contract',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
            },
        }

    patient_number = fields.Char(
        string='Broj pacijenta',
        required=True,
        index=True,
    )

    jmbg = fields.Char(
        string='JMBG',
        groups='geriatrics_19.group_patient_sensitive_data',
        copy=False,
    )

    legacy_id = fields.Integer(
        string='Odoo 8 ID pacijenta',
        index=True,
        copy=False,
    )

    id_number = fields.Char(
        string='Broj licnog dokumenta',
        groups='geriatrics_19.group_patient_sensitive_data',
    )

    active = fields.Boolean(
        string='Aktivan',
        default=True,
    )
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Kontakt', 
        required=True, 
        ondelete='restrict'
    )

    image_1920 = fields.Image(
        string='Fotografija pacijenta',
        related='partner_id.image_1920',
        readonly=False,
    )

    name = fields.Char(
        string='Ime pacijenta',
        related='partner_id.name',
        readonly=False,
    )


    lastname = fields.Char(
        string='Prezime pacijenta',
        related='partner_id.lastname',
        readonly=False,
    )

    birthdate = fields.Date(
        string='Datum rođenja',
        related='partner_id.birthdate',
        readonly=False,
    )

    age = fields.Integer(
        string='Starost',
        compute='_compute_age',
    )

    @api.depends('birthdate')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for patient in self:
            if patient.birthdate:
                birthdate = patient.birthdate
                patient.age = (
                    today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                )
            else:
                patient.age = 0

    birth_place = fields.Char(
        string='Mjesto rođenja',
        related='partner_id.birth_place',
        readonly=False,
    )

    birth_municipalities = fields.Char(
        string='Opština rođenja',
    )

    birth_country_id = fields.Many2one(
        'res.country',
        string='Država rođenja',
    )

    maiden_name = fields.Char(
        string='Djevojačko prezime',
    )

    father_name = fields.Char(
        string='Ime oca',
    )

    mother_name = fields.Char(
        string='Ime majke',
    )

    mother_surname = fields.Char(
        string='Prezime majke',
    )

    husband_name = fields.Char(
        string='Ime supružnika',
    )

    id_expiration_date = fields.Date(
        string='Datum isteka lične karte',
    )

    marital_status = fields.Selection(
        [
            ('s', 'Neoženjen/neudata'),
            ('m', 'U braku'),
            ('w', 'Udovac/udovica'),
            ('d', 'Razveden/a'),
            ('x', 'Rastavljen/a'),
        ],
        string='Bračno stanje',
    )

    blood_type = fields.Selection(
        [
            ('A', 'A'),
            ('B', 'B'),
            ('AB', 'AB'),
            ('O', 'O'),
        ],
        string='Krvna grupa',
    )

    rh = fields.Selection(
        [
            ('+', '+'),
            ('-', '-'),
        ],
        string='Rh faktor',
    )

    body_deformation_ids = fields.Many2many(
        'medical.patient.body.deformation',
        string='Tjelesni deformiteti',
    )

    mind_deformation_ids = fields.Many2many(
        'medical.patient.mind.deformation',
        string='Mentalni deformiteti',
    )

    critical_info = fields.Text(
        string='Važne medicinske informacije',
    )

    general_info = fields.Text(
        string='Opšte informacije',
    )

    deceased = fields.Boolean(
        string='Preminuo/-la',
        default=False,
    )

    dod = fields.Datetime(
        string='Datum i vrijeme smrti',
    )

    education = fields.Selection(
        [
            ('0', 'Bez obrazovanja'),
            ('1', 'Nepotpuna osnovna škola'),
            ('2', 'Osnovna škola'),
            ('3', 'Nepotpuna srednja škola'),
            ('4', 'Srednja škola'),
            ('5', 'Viša škola'),
            ('6', 'Fakultet'),
        ],
        string='Stepen obrazovanja',
    )

    occupation = fields.Many2one(
        'medical.occupation',
        string='Zanimanje',
    )

    is_pensioner = fields.Boolean(
        string='Penzioner',
        default=False,
    )

    pension_type = fields.Many2one(
        'medical.patient.pension.type',
        string='Vrsta penzije',
    )

    pension_unique_no = fields.Char(
        string='Broj penzije',
    )

    insured_via = fields.One2many(
        'medical.insurance',
        string='Osiguranje',
        related='partner_id.insurance',
        readonly=False,
    )

    property_owned = fields.Text(
        string='Imovina u vlasništvu',
    )

    ses_notes = fields.Text(
        string='Dodatne socioekonomske informacije',
    )

    sex = fields.Selection(
        related='partner_id.sex',
        string='Pol',
        readonly=False,
    )

    phone = fields.Char(
        string='Telefon',
        related='partner_id.phone',
        readonly=False,
    )

    mobile = fields.Char(
        string='Mobilni telefon',
        related='partner_id.mobile',
        readonly=False,
    )

    email = fields.Char(
        string='E-mail',
        related='partner_id.email',
        readonly=False,
    )

    street = fields.Char(
        string='Ulica i broj',
        related='partner_id.street',
        readonly=False,
    )

    street2 = fields.Char(
        string='Dodatna adresa',
        related='partner_id.street2',
        readonly=False,
    )

    zip = fields.Char(
        string='Poštanski broj',
        related='partner_id.zip',
        readonly=False,
    )

    city = fields.Char(
        string='Grad',
        related='partner_id.city',
        readonly=False,
    )

    country_id = fields.Many2one(
        'res.country',
        string='Država',
        related='partner_id.country_id',
        readonly=False,
    )

    contract_ids = fields.One2many(
        comodel_name='medical.patient.contract',
        inverse_name='patient_id',
        string='Ugovori'
    )

    tracking_list_ids = fields.One2many(
        'medical.patient.tracking.list',
        'patient_id',
        string='Evidencija rada',
    )

    activities_id = fields.Many2many(
        'medical.patient.activities',
        'medical_relation_patient_activities',
        'patient_id',
        'activity_id',
        string='Aktivnosti pacijenta',
    )

    family_relation_ids = fields.One2many(
        'geriatrics.family.relation',
        'family_partner_id',
        string='Članovi porodice',
        related='partner_id.family_relation_ids',
        readonly=True,
    )

    # Plan zaštite pacijenta
    current_functioning = fields.Text(
        string='Procjena trenutnog funkcionisanja',
    )

    adaptation_help = fields.Text(
        string='Pomoć pri adaptaciji',
    )

    family_plan = fields.Text(
        string='Plan rada s porodicom',
    )

    freetime_plan = fields.Text(
        string='Plan slobodnog vremena',
    )

    short_goals = fields.Text(
        string='Kratkoročni ciljevi',
    )

    long_goals = fields.Text(
        string='Dugoročni ciljevi',
    )

    _unique_partner = models.Constraint(
        'UNIQUE(partner_id)',
        'Ovaj kontakt je već registrovan kao pacijent.'
    )

    @api.depends('name', 'lastname')
    def _compute_display_name(self):
        for patient in self:
            full_name = ' '.join(
                part for part in [patient.name, patient.lastname]
                if part
            )
            patient.display_name = full_name or f"Pacijent {patient.id}"

    @api.model_create_multi
    def create(self, vals_list):
        partner_fields = [
            'name', 'lastname', 'birthdate', 'birth_place',
            'sex', 'phone', 'mobile', 'email',
            'street', 'street2', 'zip', 'city', 'country_id',
        ]

        for vals in vals_list:
            if not vals.get('partner_id'):
                partner_vals = {}

                for field_name in partner_fields:
                    if field_name in vals:
                        partner_vals[field_name] = vals.pop(field_name)

                if not partner_vals.get('name'):
                    raise ValueError("Ime pacijenta je obavezno.")

                partner = self.env['res.partner'].create(partner_vals)
                vals['partner_id'] = partner.id

        return super().create(vals_list)
