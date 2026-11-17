# Konsolidacija potvrđenih duplikata odjela iz Odoo 8.
# Vrijednosti su originalni Odoo 8 ID-jevi, ne Odoo 19 ID-jevi.

P5_LEGACY_IDS = {
    13, 14, 15, 16, 17, 22, 25, 27, 28,
    29, 30, 31, 32, 53, 66, 72, 73,
    74, 76, 77, 78, 79, 80, 103,
    104, 105, 143,
}

P5_CANONICAL_LEGACY_ID = 13

UNIT_LEGACY_ALIASES = {
    legacy_id: P5_CANONICAL_LEGACY_ID
    for legacy_id in P5_LEGACY_IDS
}


def canonical_unit_legacy_id(legacy_id):
    """Vraca glavni Odoo 8 ID za potvrđene duplikate."""
    return UNIT_LEGACY_ALIASES.get(legacy_id, legacy_id)