from app.models.analyse_photo_etiquette import AnalysePhotoEtiquette
from app.models.bareme import BAREME_TYPES, Bareme
from app.models.bat_reference import BAT_MIME_TYPES_AUTORISES, BatReference
from app.models.catalogue import Catalogue
from app.models.charge_machine_mensuelle import ChargeMachineMensuelle
from app.models.charge_mensuelle import ChargeMensuelle
from app.models.client import Client
from app.models.complexe import Complexe
from app.models.config_changements import ConfigChangements
from app.models.config_couts import ConfigCouts
from app.models.config_roulage import MODES_ROULAGE, ConfigRoulage
from app.models.configuration_pose import ConfigurationPose
from app.models.controle_bat import (
    ACTIONS_CORRECTION_SENS,
    DECISIONS_FINALES,
    DECISIONS_RECOMMANDEES,
    NIVEAUX_CONFIANCE,
    ControleBat,
)
from app.models.correspondance_laize_metrage import CorrespondanceLaizeMetrage
from app.models.cylindre_magnetique import CylindreMagnetique
from app.models.devis import Devis
from app.models.entreprise import Entreprise
from app.models.lot_production import LotProduction
from app.models.fournisseur import Fournisseur
from app.models.machine import Machine
from app.models.machine_imprimerie import MachineImprimerie
from app.models.machine_rebobineuse import MachineRebobineuse
from app.models.matiere import Matiere
from app.models.parametre_mandrin import MODES_PAR_DEFAUT, ParametreMandrin
from app.models.operation_finition import OperationFinition
from app.models.option_fabrication import OptionFabrication
from app.models.outil_decoupe import OutilDecoupe
from app.models.partenaire_st import PartenaireST
from app.models.photo_production import PHOTO_TYPE_ETAPES, PhotoProduction
from app.models.porte_cliche import PorteCliche
from app.models.rapport_qualite_production import RapportQualiteProduction
from app.models.tarif_encre import TarifEncre
from app.models.tarif_poste import TarifPoste
from app.models.temps_operation_standard import TempsOperationStandard
from app.models.user import User

__all__ = [
    # Sprint 13 Lot S13.E — POC IA analyse photo étiquette (FlexoCheck)
    "AnalysePhotoEtiquette",
    # Sprint 13 Lot S13.B — 6 modèles métier pour le moteur d'optimisation
    "BAREME_TYPES",
    "Bareme",
    "ConfigurationPose",
    "CylindreMagnetique",
    "MachineImprimerie",
    "Matiere",
    "OptionFabrication",
    # Sprint 13 Lot S13.F — 2 tables traçabilité (fondations FlexoCheck)
    "PHOTO_TYPE_ETAPES",
    "PhotoProduction",
    "RapportQualiteProduction",
    # Sprint 15 Lot 1 — Contrôle BAT IA (FlexoCheck)
    "ACTIONS_CORRECTION_SENS",
    "ControleBat",
    "DECISIONS_FINALES",
    "DECISIONS_RECOMMANDEES",
    "NIVEAUX_CONFIANCE",
    # Sprint 15 Lot 3 — BAT de référence par devis
    "BAT_MIME_TYPES_AUTORISES",
    "BatReference",
    # Sprint 16 Lot A — Module Rebobinage
    "MachineRebobineuse",
    "MODES_PAR_DEFAUT",
    "ParametreMandrin",
    # Brief stratégique v2 Phase 1 — socle Stratégique (config par entreprise)
    "ConfigChangements",
    "ConfigCouts",
    "ConfigRoulage",
    "MODES_ROULAGE",
    # Modèles existants (Sprint 0 à 12)
    "Catalogue",
    "ChargeMachineMensuelle",
    "ChargeMensuelle",
    "Client",
    "Complexe",
    "CorrespondanceLaizeMetrage",
    "Devis",
    "Entreprise",
    "Fournisseur",
    # Sprint 13 avenant — multi-lots production
    "LotProduction",
    "Machine",
    "OperationFinition",
    "OutilDecoupe",
    "PartenaireST",
    # Brief #29 — paramètres parc (sleeves / porte-clichés)
    "PorteCliche",
    "TarifEncre",
    "TarifPoste",
    "TempsOperationStandard",
    "User",
]
