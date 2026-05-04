from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChargeMachineMensuelle(Base):
    """Charge mensuelle d'une machine — coût horaire calculé par hook applicatif.

    `cout_horaire_calcule = montant_total / heures_disponibles` est recalculé
    à chaque INSERT/UPDATE via `before_insert` / `before_update` (cf. bas du
    module). Style aligné sur le repo : pas d'`hybrid_property`.
    """

    __tablename__ = "charge_machine_mensuelle"
    __table_args__ = (
        CheckConstraint("mois BETWEEN 1 AND 12", name="ck_charge_machine_mois"),
        CheckConstraint("annee >= 2024", name="ck_charge_machine_annee"),
        UniqueConstraint("mois", "annee", name="uq_charge_machine_mois_annee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    mois: Mapped[int] = mapped_column(Integer, nullable=False)
    annee: Mapped[int] = mapped_column(Integer, nullable=False)
    montant_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    heures_disponibles: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    cout_horaire_calcule: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(100))

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def _recompute_cout_horaire(_mapper, _connection, target: ChargeMachineMensuelle) -> None:
    # Interdit la division par zéro plutôt que de laisser SQL planter sans contexte.
    if target.heures_disponibles is None or Decimal(target.heures_disponibles) == 0:
        raise ValueError(
            "ChargeMachineMensuelle.heures_disponibles doit être > 0"
        )
    target.cout_horaire_calcule = (
        Decimal(target.montant_total) / Decimal(target.heures_disponibles)
    ).quantize(Decimal("0.0001"))


event.listen(ChargeMachineMensuelle, "before_insert", _recompute_cout_horaire)
event.listen(ChargeMachineMensuelle, "before_update", _recompute_cout_horaire)
