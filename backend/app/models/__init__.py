from app.models.bareme import BAREME_TYPES, Bareme
from app.models.catalogue import Catalogue
from app.models.charge_machine_mensuelle import ChargeMachineMensuelle
from app.models.charge_mensuelle import ChargeMensuelle
from app.models.client import Client
from app.models.complexe import Complexe
from app.models.configuration_pose import ConfigurationPose
from app.models.correspondance_laize_metrage import CorrespondanceLaizeMetrage
from app.models.cylindre_magnetique import CylindreMagnetique
from app.models.devis import Devis
from app.models.entreprise import Entreprise
from app.models.fournisseur import Fournisseur
from app.models.machine import Machine
from app.models.machine_imprimerie import MachineImprimerie
from app.models.matiere import Matiere
from app.models.operation_finition import OperationFinition
from app.models.option_fabrication import OptionFabrication
from app.models.outil_decoupe import OutilDecoupe
from app.models.partenaire_st import PartenaireST
from app.models.photo_production import PHOTO_TYPE_ETAPES, PhotoProduction
from app.models.rapport_qualite_production import RapportQualiteProduction
from app.models.tarif_encre import TarifEncre
from app.models.tarif_poste import TarifPoste
from app.models.temps_operation_standard import TempsOperationStandard
from app.models.user import User

__all__ = [
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
    "Machine",
    "OperationFinition",
    "OutilDecoupe",
    "PartenaireST",
    "TarifEncre",
    "TarifPoste",
    "TempsOperationStandard",
    "User",
]
