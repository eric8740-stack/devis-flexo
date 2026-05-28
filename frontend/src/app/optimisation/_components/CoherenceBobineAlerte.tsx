"use client";

/**
 * Alerte cohérence Ø extérieur ↔ nb étiquettes/bobine (saisie devis).
 *
 * Souveraineté commerciale : alerte **non bloquante**, le commercial peut
 * forcer. UX : texte visible sous les champs Ø / nb étiq (mobile-first,
 * jamais de tooltip survol). Color-codée : ⚠️ ambre / ℹ️ bleu / ✅ vert.
 *
 * Source de vérité = backend (`POST /api/devis/coherence-bobine` →
 * `bat_calculs`). On NE recode PAS la formule ici, garantie zéro drift
 * avec le 242 mm de la VUE B.
 *
 * Appel debouncé (400 ms) à chaque évolution des inputs. Pas d'appel
 * tant que les inputs requis ne sont pas tous renseignés (Ø > 0,
 * nb > 0, mandrin > 0, pas > 0).
 */
import { useEffect, useState } from "react";

import {
  checkCoherenceBobine,
  type CoherenceBobineResponse,
} from "@/lib/api";

import { useOptimisationPose } from "./OptimisationPoseStore";

interface Props {
  /** Développé étiquette (mm), saisi étape 1 (format.hauteur_mm). */
  devEtiqMm: number;
  /** Intervalle dev approx (saisi étape 1 — proxy pour ecart_dev moteur). */
  ecartDevMm: number;
  /** Mandrin (mm), saisi étape 1. */
  mandrinMm: number;
  /**
   * Épaisseur matière depuis le catalogue (µm) si une matière a été
   * sélectionnée à la saisie. null → fallback backend (150 µm) signalé
   * dans la réponse via `epaisseur_source`.
   */
  epaisseurCatalogueUm: number | null;
}

export function CoherenceBobineAlerte({
  devEtiqMm,
  ecartDevMm,
  mandrinMm,
  epaisseurCatalogueUm,
}: Props) {
  const { briefClient, clientSelectionne } = useOptimisationPose();
  const nbEtiq = briefClient.nb_etiquettes_par_rouleau ?? null;
  const diametreSaisi = briefClient.diametre_max_bobine_mm ?? null;
  const dmaxClient = clientSelectionne?.diametre_max_bobine_mm ?? null;
  const pasMm = devEtiqMm + ecartDevMm;

  const [result, setResult] = useState<CoherenceBobineResponse | null>(null);
  const [erreurReseau, setErreurReseau] = useState<string | null>(null);

  useEffect(() => {
    // Pré-conditions : tous les inputs nécessaires sont renseignés et > 0.
    if (
      nbEtiq === null ||
      nbEtiq <= 0 ||
      diametreSaisi === null ||
      diametreSaisi <= 0 ||
      mandrinMm <= 0 ||
      pasMm <= 0
    ) {
      setResult(null);
      setErreurReseau(null);
      return;
    }
    let cancelled = false;
    const handle = setTimeout(() => {
      checkCoherenceBobine({
        diametre_ext_saisi_mm: diametreSaisi,
        nb_etiq_saisi: nbEtiq,
        mandrin_mm: mandrinMm,
        pas_mm: pasMm,
        epaisseur_catalogue_um: epaisseurCatalogueUm,
        diametre_max_client_mm: dmaxClient,
      })
        .then((res) => {
          if (!cancelled) {
            setResult(res);
            setErreurReseau(null);
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setResult(null);
            setErreurReseau(
              err instanceof Error ? err.message : "Erreur inconnue",
            );
          }
        });
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [
    nbEtiq,
    diametreSaisi,
    mandrinMm,
    pasMm,
    epaisseurCatalogueUm,
    dmaxClient,
  ]);

  if (erreurReseau !== null) {
    return (
      <p
        data-testid="coherence-bobine-erreur"
        className="text-xs text-muted-foreground"
      >
        Vérif cohérence indisponible : {erreurReseau}
      </p>
    );
  }
  if (result === null) return null;

  return (
    <div
      data-testid="coherence-bobine-alerte"
      data-severity={result.severity}
      className="space-y-1.5 text-sm"
    >
      {/* Cohérence Ø ↔ nb étiq (check 1). */}
      {result.severity === "warning" && (
        <p
          role="alert"
          data-testid="coherence-bobine-warning"
          className="rounded-md border-l-4 border-l-amber-500 bg-amber-50 px-3 py-2 text-amber-900"
        >
          ⚠ {result.message}
        </p>
      )}
      {result.severity === "info" && (
        <p
          data-testid="coherence-bobine-info"
          className="rounded-md border-l-4 border-l-blue-500 bg-blue-50 px-3 py-2 text-blue-900"
        >
          ℹ {result.message}
        </p>
      )}
      {result.severity === "ok" && (
        <p
          data-testid="coherence-bobine-ok"
          className="rounded-md border-l-4 border-l-emerald-500 bg-emerald-50 px-3 py-2 text-emerald-900"
        >
          ✓ Cohérent — Ø permet ≈ {result.nb_max} étiq (saisi {nbEtiq}).
        </p>
      )}

      {/* Check fit machine client (check 2, indépendant). */}
      {result.fit_severity === "warning" && result.fit_message !== null && (
        <p
          role="alert"
          data-testid="coherence-bobine-fit-warning"
          className="rounded-md border-l-4 border-l-amber-500 bg-amber-50 px-3 py-2 text-amber-900"
        >
          ⚠ {result.fit_message}
        </p>
      )}

      {/* Signalement source épaisseur si fallback. */}
      {result.epaisseur_source === "fallback" && (
        <p className="text-xs text-muted-foreground">
          Épaisseur matière fallback {result.epaisseur_appliquee_um} µm
          (catalogue absent — sélectionne la matière à la saisie pour un
          check plus précis).
        </p>
      )}
    </div>
  );
}
