{
    'name': 'Gerijatrija',
    'version': '19.0.1.0.0',
    'summary': 'Evidencija pacijenata gerijatrijske ustanove',
    'category': 'Healthcare',
    'author': 'Voyin',
    'depends': ['base', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/relationship_types.xml',
        'views/patient_views.xml',
        'views/patient_contract_views.xml',
        'views/partner_views.xml',
        'views/patient_activity_views.xml'
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}    