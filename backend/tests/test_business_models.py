"""Tests smoke des 6 modèles métier Sprint 13 Lot S13.B.

Pour chaque modèle : un test de création basique qui vérifie que :
  - La table est créée (CREATE TABLE de la migration tient)
  - Les contraintes essentielles tiennent (NOT NULL, types Decimal/JSON)
  - L'objet se persiste et se relit avec les mêmes valeurs

On ne teste PAS la logique métier ici (c'est pour Lot S13.D), juste
l'intégrité du schéma. Multi-tenancy = un test global qui vérifie que
les FK CASCADE fonctionnent (suppression entreprise → suppression rows
des 6 tables liées).
"""
from decimal import Decimal

from app.db import SessionLocal
from app.models import (
    BAREME_TYPES,
    Bareme,
    ConfigurationPose,
    CylindreMagnetique,
    Entreprise,
    MachineImprimerie,
    Matiere,
    OptionFabrication,
)


# ---------------------------------------------------------------------------
# Helpers — créer une entreprise dédiée test pour chaque modèle
# ---------------------------------------------------------------------------


def _ensure_entreprise_for_test(entreprise_id: int, label: str) -> int:
    """Crée (idempotent) une entreprise pour les tests de modèles. Renvoie
    son id. On n'utilise PAS l'entreprise demo (id=1) pour éviter de polluer
    les invariants sacrés EXACT.
    """
    db = SessionLocal()
    try:
        existing = db.query(Entreprise).filter(Entreprise.id == entreprise_id).first()
        if existing is not None:
            return existing.id
        ent = Entreprise(
            id=entreprise_id,
            raison_sociale=f"Test S13.B {label}",
            siret=f"{entreprise_id:014d}",
            email=f"test-{entreprise_id}@s13b.fr",
            is_demo=False,
        )
        db.add(ent)
        db.commit()
        return ent.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests par modèle
# ---------------------------------------------------------------------------


def test_cylindre_magnetique_create_and_read():
    ent_id = _ensure_entreprise_for_test(100, "cylindre")
    db = SessionLocal()
    try:
        cyl = CylindreMagnetique(
            entreprise_id=ent_id,
            developpe_mm=Decimal("96.00"),
            machine_repere="2200 #1",
            nb_pc_2200=3,
        )
        db.add(cyl)
        db.commit()
        db.refresh(cyl)
        assert cyl.id is not None
        assert cyl.developpe_mm == Decimal("96.00")
        assert cyl.actif is True  # default
        assert cyl.nb_pc_10p == 0  # default
        assert cyl.nb_pc_2200 == 3
    finally:
        db.close()


def test_machine_imprimerie_vitesse_pratique_required():
    ent_id = _ensure_entreprise_for_test(101, "machine_imp")
    db = SessionLocal()
    try:
        mach = MachineImprimerie(
            entreprise_id=ent_id,
            nom="Mark Andy 2200 test",
            marque="Mark Andy",
            modele="2200",
            laize_totale_mm=Decimal("330.00"),
            laize_utile_mm=Decimal("320.00"),
            nb_groupes_couleurs=8,
            # vitesse_pratique_m_min : valeur réaliste imprimeur (PAS la
            # vitesse catalogue, qui serait ~250+ m/min sur ce modèle).
            vitesse_pratique_m_min=80,
            options=["UV", "dorure_froid"],
        )
        db.add(mach)
        db.commit()
        db.refresh(mach)
        assert mach.id is not None
        assert mach.vitesse_pratique_m_min == 80
        assert mach.nb_postes_decoupe == 1  # default
        assert mach.options == ["UV", "dorure_froid"]
    finally:
        db.close()


def test_matiere_transparence_et_certifications():
    ent_id = _ensure_entreprise_for_test(102, "matiere")
    db = SessionLocal()
    try:
        mat = Matiere(
            entreprise_id=ent_id,
            code="BOPP_TRANSP_50",
            libelle="BOPP transparent 50 microns",
            categorie="film",
            epaisseur_microns=50,
            est_transparent=True,  # déclenche règle spot détection verso
            opacite_pct=Decimal("5.0"),
            certifications_env=["FSC_mixte", "ecolabel_eu"],
        )
        db.add(mat)
        db.commit()
        db.refresh(mat)
        assert mat.id is not None
        assert mat.est_transparent is True
        assert mat.certifications_env == ["FSC_mixte", "ecolabel_eu"]
        assert mat.adhesifs_compatibles is None  # nullable
    finally:
        db.close()


def test_option_fabrication_global_catalog_nullable_entreprise():
    """option_fabrication.entreprise_id est NULLABLE pour le catalogue global."""
    db = SessionLocal()
    try:
        opt = OptionFabrication(
            entreprise_id=None,  # = catalogue global
            code="dorure_chaud",
            libelle="Dorure à chaud (hot foil)",
            categorie="Finition",
            groupes_couleurs_requis=0,
            modules_speciaux_requis=["hot_stamping"],
            ajoute_temps_calage_min=25,
            coef_vitesse_impact=Decimal("0.75"),
            coef_gache_impact=Decimal("1.15"),
        )
        db.add(opt)
        db.commit()
        db.refresh(opt)
        assert opt.id is not None
        assert opt.entreprise_id is None
        assert opt.coef_vitesse_impact == Decimal("0.75")
        assert opt.modules_speciaux_requis == ["hot_stamping"]
    finally:
        db.close()


def test_bareme_type_field_and_json_data():
    ent_id = _ensure_entreprise_for_test(103, "bareme")
    db = SessionLocal()
    try:
        bar = Bareme(
            entreprise_id=ent_id,
            type="effet_banane",
            nom="Barème ICE 2024",
            bareme_data=[
                {"largeur_max_mm": 150, "developpe_mini_mm": 80},
                {"largeur_max_mm": 350, "developpe_mini_mm": 160},
            ],
        )
        db.add(bar)
        db.commit()
        db.refresh(bar)
        assert bar.id is not None
        assert bar.type == "effet_banane"
        assert bar.type in BAREME_TYPES
        assert len(bar.bareme_data) == 2
        assert bar.bareme_data[1]["developpe_mini_mm"] == 160
        assert bar.actif is True
    finally:
        db.close()


def test_configuration_pose_minimal_fields():
    ent_id = _ensure_entreprise_for_test(104, "config_pose")
    db = SessionLocal()
    try:
        # Need a cylindre + machine_imprimerie pour les FK NOT NULL
        cyl = CylindreMagnetique(
            entreprise_id=ent_id, developpe_mm=Decimal("104.00")
        )
        mach = MachineImprimerie(
            entreprise_id=ent_id,
            nom="Test machine config_pose",
            laize_totale_mm=Decimal("330.00"),
            laize_utile_mm=Decimal("320.00"),
            vitesse_pratique_m_min=70,
        )
        db.add_all([cyl, mach])
        db.commit()

        config = ConfigurationPose(
            entreprise_id=ent_id,
            devis_id=None,  # nullable : config en simulation
            cylindre_id=cyl.id,
            machine_id=mach.id,
            nb_poses_dev=12,
            nb_poses_laize=4,
            nb_poses_total=48,
            intervalle_dev_reel_mm=Decimal("3.50"),
            qualite_echenillage="parfait",
            type_config="optimale",
            score=Decimal("95.50"),
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        assert config.id is not None
        assert config.devis_id is None
        assert config.nb_poses_total == 48
        # Defaults
        assert config.disposition_poses == "alignee"
        assert config.coef_vitesse == Decimal("1.00")
        assert config.consolidation_atteinte is False
        assert config.forcage_manuel is False
        assert config.est_retenue is False
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Test global multi-tenant : suppression entreprise → CASCADE sur les 5
# tables avec entreprise_id NOT NULL (option_fabrication exclue car nullable)
# ---------------------------------------------------------------------------


def test_cascade_delete_entreprise_removes_business_rows():
    """Suppression d'une entreprise → CASCADE sur les 5 tables business
    qui ont entreprise_id NOT NULL FK CASCADE.

    option_fabrication avec entreprise_id=NULL (catalogue global) doit
    en revanche survivre — c'est tout l'intérêt du nullable.
    """
    db = SessionLocal()
    try:
        # Cleanup idempotent : les autouse fixtures re-seedent l'entreprise
        # demo, mais ne touchent PAS aux 6 nouvelles tables S13.B. Si un
        # run précédent a laissé une option globale "cascade-global", elle
        # survit entre les runs. On la supprime au début pour repartir
        # propre. Idem pour l'entreprise siret 99999... du précédent run.
        db.query(OptionFabrication).filter_by(code="cascade-global").delete()
        db.query(OptionFabrication).filter_by(code="cascade-opt").delete()
        db.query(Entreprise).filter_by(siret="99999999999999").delete()
        db.commit()

        ent = Entreprise(
            raison_sociale="Cascade Test S13.B",
            siret="99999999999999",
            email="cascade@s13b.fr",
            is_demo=False,
        )
        db.add(ent)
        db.commit()
        ent_id = ent.id

        # 1 row dans chacune des 5 tables business + 1 option globale qui doit survivre
        db.add_all([
            CylindreMagnetique(entreprise_id=ent_id, developpe_mm=Decimal("90")),
            MachineImprimerie(
                entreprise_id=ent_id,
                nom="cascade-machine",
                laize_totale_mm=Decimal("330"),
                laize_utile_mm=Decimal("320"),
                vitesse_pratique_m_min=60,
            ),
            Matiere(entreprise_id=ent_id, code="cascade", libelle="cascade test"),
            OptionFabrication(
                entreprise_id=ent_id, code="cascade-opt", libelle="override"
            ),
            Bareme(entreprise_id=ent_id, type="echenillage", bareme_data=[]),
        ])
        # Option globale (entreprise_id=None) — doit survivre à la suppression
        db.add(
            OptionFabrication(
                entreprise_id=None, code="cascade-global", libelle="catalogue global"
            )
        )
        db.commit()

        # Sanity : 1 row par table business
        assert (
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).count() == 1
        )

        # Suppression entreprise → CASCADE
        db.delete(ent)
        db.commit()

        assert (
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).count() == 0
        )
        assert (
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).count() == 0
        )
        assert db.query(Matiere).filter_by(entreprise_id=ent_id).count() == 0
        assert (
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).count() == 0
        )
        assert db.query(Bareme).filter_by(entreprise_id=ent_id).count() == 0

        # L'option globale survit
        assert (
            db.query(OptionFabrication)
            .filter_by(code="cascade-global", entreprise_id=None)
            .count()
            == 1
        )
    finally:
        db.close()
