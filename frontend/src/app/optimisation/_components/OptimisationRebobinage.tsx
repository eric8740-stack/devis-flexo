"use client";

/**
 * Sprint 16 Lot D — Étape Rebobinage (câblage backend Lots A/B/C).
 *
 * Insérée APRÈS l'optimisation de pose (étape "detail") et AVANT le
 * chiffrage final. Trois rôles :
 *
 *   1. Saisir / ajuster les paramètres bobine du client (diamètre
 *      mandrin, diamètre max bobine, nb étiq/bobine fixe optionnel).
 *      Pré-remplis depuis le brief client + saisie initiale ; le
 *      pré-remplissage du profil client complet (marquage, film,
 *      conditionnement…) attend l'ALTER client 9 colonnes (commit 2).
 *
 *   2. Afficher le calcul auto (nb bobines, temps, coût) et
 *      l'arbitrage pré-coupé vs découpe interne renvoyés par
 *      `POST /api/rebobinage/calculer` (Lot C).
 *
 *   3. Souveraineté commerciale : le commercial peut FORCER un mode
 *      (pré-coupé ou découpe interne). L'UI exige un motif ≥10 chars
 *      pour traçabilité — le backend tolère plus court (cf.
 *      arbitrage_mandrins.py) ; on choisit la version stricte.
 *
 * Mobile-first : grilles 1 col par défaut → 2 col en sm+. Pas de
 * tooltip au survol — toute info utile en texte visible.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  postRebobinageCalculer,
  type ModeRebobinageApplique,
  type ModeRebobinageIn,
  type RebobinageCalculerRequest,
  type RebobinageResultat,
} from "@/lib/api";
import { cn } from "@/lib/utils";

import { useClientsListe } from "./useClientsListe";
import { useOptimisationPose } from "./OptimisationPoseStore";
import { useRebobineusesDuTenant } from "./useRebobineusesDuTenant";

const MODE_LABEL: Record<ModeRebobinageApplique, string> = {
  pre_coupe: "Pré-coupé",
  decoupe_interne: "Découpe interne",
};

const MODE_DESCRIPTION: Record<ModeRebobinageApplique, string> = {
  pre_coupe:
    "Mandrins reçus déjà coupés à la longueur. Pas d'usinage interne, mise en route rapide.",
  decoupe_interne:
    "Mandrins découpés en interne avant rebobinage. Cycle plus long mais flexible sur les longueurs.",
};

// Diamètres mandrin courants flexo (alignés sur la saisie étape 1).
const DIAMETRES_MANDRIN_MM = [25, 38, 40, 50, 76] as const;

// Tarifs mandrins par défaut UI (à confirmer / persister au commit 2 quand
// le profil tenant exposera ses tarifs propres). Documenté ici pour que
// le commercial sache d'où vient le calcul tant qu'on n'a pas de dropdown
// "Tarifs catalogue".
const TARIFS_DEFAULTS = {
  prix_pre_coupe_par_mandrin_eur: "0.50",
  cout_decoupe_interne_par_mandrin_eur: "0.15",
  cout_fixe_decoupe_interne_eur: "5.00",
};

const MOTIF_MIN_LENGTH = 10;

export function OptimisationRebobinage() {
  const {
    briefClient,
    mandrinMm,
    sommeQuantitesLots,
    quantiteTotale,
    selection,
    goDetail,
    goChiffrage,
    setRebobinage,
    rebobinageRequest,
    clientSelectionne,
    setClientSelectionne,
    sensEnroulementClient,
    setSensEnroulementClient,
  } = useOptimisationPose();

  // ──────────────────────────────────────────────────────────────────
  // Sélecteur client en tête (Sprint 16 auto-fill).
  // Source de vérité : le store ; ce composant ne fait que lire/écrire
  // `clientSelectionne` qui sera aussi consommé par OptimisationChiffrage
  // pour pré-remplir son select et propager `client_id` au POST devis.
  // ──────────────────────────────────────────────────────────────────
  const {
    clients,
    loading: clientsLoading,
    error: clientsError,
  } = useClientsListe();

  // ──────────────────────────────────────────────────────────────────
  // Sélection rebobineuse (correctif fin du hardcode id=1).
  // Le hook fournit la liste des rebobineuses du tenant ; on auto-sélectionne
  // si N=1, on rend un select si N>1, et on bloque le calcul si N=0.
  // ──────────────────────────────────────────────────────────────────
  const {
    machines: rebobineuses,
    loading: rebobineusesLoading,
    error: rebobineusesError,
  } = useRebobineusesDuTenant();

  const [machineRebobineuseId, setMachineRebobineuseId] = useState<
    number | null
  >(rebobinageRequest?.machine_rebobineuse_id ?? null);

  // Auto-sélection de la 1ère rebobineuse une fois la liste chargée, si
  // rien n'a été choisi via un retour-depuis-chiffrage.
  useEffect(() => {
    if (machineRebobineuseId === null && rebobineuses.length > 0) {
      setMachineRebobineuseId(rebobineuses[0]!.id);
    }
  }, [machineRebobineuseId, rebobineuses]);

  // ──────────────────────────────────────────────────────────────────
  // Pré-remplissage initial (au mount). Ordre de priorité :
  //   1. valeur déjà saisie dans le store rebobinage (retour depuis
  //      l'étape chiffrage)
  //   2. profil rebobinage du client sélectionné (Sprint 16 auto-fill)
  //   3. brief client de la saisie étape 1 / mandrin choisi étape 1
  // L'utilisateur peut overrider chaque valeur via les inputs.
  // ──────────────────────────────────────────────────────────────────
  const initialMandrin =
    rebobinageRequest?.profil_client.diametre_mandrin_mm ??
    clientSelectionne?.diametre_mandrin_mm ??
    mandrinMm;
  const initialDiamMax =
    rebobinageRequest?.profil_client.diametre_max_bobine_mm !== undefined &&
    rebobinageRequest?.profil_client.diametre_max_bobine_mm !== null
      ? String(rebobinageRequest.profil_client.diametre_max_bobine_mm)
      : clientSelectionne?.diametre_max_bobine_mm != null
        ? String(clientSelectionne.diametre_max_bobine_mm)
        : briefClient.diametre_max_bobine_mm !== null
          ? String(briefClient.diametre_max_bobine_mm)
          : "";
  const initialNbEtiq =
    rebobinageRequest?.profil_client.nb_etiq_par_bobine_fixe != null
      ? String(rebobinageRequest.profil_client.nb_etiq_par_bobine_fixe)
      : clientSelectionne?.nb_etiq_par_bobine_fixe != null
        ? String(clientSelectionne.nb_etiq_par_bobine_fixe)
        : briefClient.nb_etiquettes_par_rouleau !== null
          ? String(briefClient.nb_etiquettes_par_rouleau)
          : "";

  const [diametreMandrin, setDiametreMandrin] =
    useState<number>(initialMandrin);
  const [diametreMaxBobine, setDiametreMaxBobine] =
    useState<string>(initialDiamMax);
  const [nbEtiqParBobine, setNbEtiqParBobine] = useState<string>(initialNbEtiq);

  // Sprint 16 auto-fill — quand l'utilisateur change le client en cours
  // de session (sélecteur en tête), on remet à plat les 3 inputs avec
  // les nouvelles valeurs profil. Comportement explicite et prévisible :
  // changer de client réinitialise les inputs au profil de ce client ;
  // l'opérateur peut ensuite overrider à la main.
  // Le 1er mount est couvert par les `initial*` ci-dessus — on évite la
  // double application via une ref qui track le dernier client appliqué.
  const lastAppliedClientId = useState<number | null>(
    clientSelectionne?.id ?? null,
  );
  useEffect(() => {
    const currentId = clientSelectionne?.id ?? null;
    if (currentId === lastAppliedClientId[0]) return;
    lastAppliedClientId[1](currentId);
    if (clientSelectionne === null) return;
    if (clientSelectionne.diametre_mandrin_mm !== null) {
      setDiametreMandrin(clientSelectionne.diametre_mandrin_mm);
    }
    if (clientSelectionne.diametre_max_bobine_mm !== null) {
      setDiametreMaxBobine(String(clientSelectionne.diametre_max_bobine_mm));
    }
    if (clientSelectionne.nb_etiq_par_bobine_fixe !== null) {
      setNbEtiqParBobine(String(clientSelectionne.nb_etiq_par_bobine_fixe));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientSelectionne]);

  // Tarifs mandrins (defaults projet UI tant que pas de catalogue tenant).
  const [prixPreCoupe, setPrixPreCoupe] = useState<string>(
    rebobinageRequest?.tarifs_mandrins.prix_pre_coupe_par_mandrin_eur ??
      TARIFS_DEFAULTS.prix_pre_coupe_par_mandrin_eur,
  );
  const [coutDecoupeInterne, setCoutDecoupeInterne] = useState<string>(
    rebobinageRequest?.tarifs_mandrins.cout_decoupe_interne_par_mandrin_eur ??
      TARIFS_DEFAULTS.cout_decoupe_interne_par_mandrin_eur,
  );
  const [coutFixeDecoupeInterne, setCoutFixeDecoupeInterne] =
    useState<string>(
      rebobinageRequest?.tarifs_mandrins.cout_fixe_decoupe_interne_eur ??
        TARIFS_DEFAULTS.cout_fixe_decoupe_interne_eur,
    );

  // Forçage commercial : mode + motif obligatoire si activé.
  const [forcerMode, setForcerMode] = useState<boolean>(
    rebobinageRequest ? rebobinageRequest.mode !== "auto" : false,
  );
  const [modeForce, setModeForce] = useState<ModeRebobinageApplique>(
    (rebobinageRequest?.mode === "pre_coupe" ||
      rebobinageRequest?.mode === "decoupe_interne")
      ? rebobinageRequest.mode
      : "pre_coupe",
  );
  const [motifForce, setMotifForce] = useState<string>(
    rebobinageRequest?.motif_force ?? "",
  );
  const [motifErreur, setMotifErreur] = useState<string | null>(null);

  // ──────────────────────────────────────────────────────────────────
  // Spec lot : on lit intervalle_dev + épaisseur depuis le 1er candidat
  // sélectionné en étape "detail". Si pas de selection (cas dégradé), on
  // utilise des defaults — le backend lèvera une erreur si tout est
  // incohérent, l'UI l'affiche.
  // ──────────────────────────────────────────────────────────────────
  const premierCandidat = selection[0]?.candidat ?? null;
  const intervalleDevMm = premierCandidat?.intervalle_dev_applique_mm ?? 2;
  const epaisseurMatiereUm = premierCandidat?.epaisseur_appliquee_um ?? 150;
  const epaisseurMatiereMm = epaisseurMatiereUm / 1000;

  const nbEtiquettesTotal = sommeQuantitesLots || quantiteTotale || 0;
  const parsedNbEtiqBobine = parseInt(nbEtiqParBobine, 10);
  const nbEtiqBobineFixe =
    Number.isFinite(parsedNbEtiqBobine) && parsedNbEtiqBobine > 0
      ? parsedNbEtiqBobine
      : null;
  const parsedDiamMax = parseInt(diametreMaxBobine, 10);
  const diametreMaxValide =
    Number.isFinite(parsedDiamMax) && parsedDiamMax > 0 ? parsedDiamMax : null;

  // ──────────────────────────────────────────────────────────────────
  // Construit le payload backend depuis les inputs UI.
  // Retourne null si paramètres incomplets (diamMax manquant) pour
  // éviter un fetch inutile.
  // ──────────────────────────────────────────────────────────────────
  const buildRequest = useCallback((): RebobinageCalculerRequest | null => {
    if (nbEtiquettesTotal <= 0 || diametreMaxValide === null) return null;
    // Garde "0 rebobineuse" : sans machine sélectionnée, on ne peut PAS
    // partir au backend (404 garanti). Le composant affiche un message
    // d'erreur explicite plus bas, mais on coupe ici pour ne pas tenter
    // un fetch certain de tomber.
    if (machineRebobineuseId === null) return null;
    const mode: ModeRebobinageIn = forcerMode ? modeForce : "auto";
    const motif = forcerMode ? motifForce.trim() : null;
    return {
      spec_lot: {
        nb_etiquettes_total: nbEtiquettesTotal,
        intervalle_developpe_mm: String(intervalleDevMm),
        epaisseur_matiere_mm: String(epaisseurMatiereMm),
      },
      profil_client: {
        diametre_mandrin_mm: diametreMandrin,
        diametre_max_bobine_mm: diametreMaxValide,
        nb_etiq_par_bobine_fixe: nbEtiqBobineFixe,
      },
      machine_rebobineuse_id: machineRebobineuseId,
      tarifs_mandrins: {
        prix_pre_coupe_par_mandrin_eur: prixPreCoupe,
        cout_decoupe_interne_par_mandrin_eur: coutDecoupeInterne,
        cout_fixe_decoupe_interne_eur: coutFixeDecoupeInterne,
      },
      mode,
      motif_force: motif && motif.length > 0 ? motif : null,
    };
  }, [
    nbEtiquettesTotal,
    diametreMaxValide,
    machineRebobineuseId,
    forcerMode,
    modeForce,
    motifForce,
    intervalleDevMm,
    epaisseurMatiereMm,
    diametreMandrin,
    nbEtiqBobineFixe,
    prixPreCoupe,
    coutDecoupeInterne,
    coutFixeDecoupeInterne,
  ]);

  // ──────────────────────────────────────────────────────────────────
  // Calcul rebobinage (preview, pas de persist côté backend).
  // ──────────────────────────────────────────────────────────────────
  const [result, setResult] = useState<RebobinageResultat | null>(
    null,
  );
  const [calculLoading, setCalculLoading] = useState<boolean>(false);
  const [calculError, setCalculError] = useState<string | null>(null);

  const calculer = useCallback(async () => {
    const req = buildRequest();
    if (req === null) {
      setCalculError(
        "Renseignez Ø max bobine et vérifiez la quantité totale avant de lancer le calcul.",
      );
      return;
    }
    setCalculLoading(true);
    setCalculError(null);
    try {
      const res = await postRebobinageCalculer(req);
      setResult(res);
    } catch (err) {
      setResult(null);
      setCalculError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setCalculLoading(false);
    }
  }, [buildRequest]);

  // Calcul auto déclenché par l'arrivée d'une rebobineuse sélectionnée
  // (auto-sélection initiale OU changement utilisateur dans le select).
  // Recalcul des autres paramètres = bouton "Recalculer" manuel pour ne
  // pas spammer l'API à chaque frappe d'input.
  useEffect(() => {
    if (
      !calculLoading &&
      diametreMaxValide &&
      machineRebobineuseId !== null
    ) {
      void calculer();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machineRebobineuseId]);

  const modeRetenuFinal: ModeRebobinageApplique = useMemo(() => {
    if (result?.arbitrage.mode_applique) {
      return result.arbitrage.mode_applique;
    }
    return forcerMode ? modeForce : "pre_coupe";
  }, [result, forcerMode, modeForce]);

  // ──────────────────────────────────────────────────────────────────
  // Validation & navigation
  // ──────────────────────────────────────────────────────────────────
  const validerEtContinuer = async () => {
    if (forcerMode) {
      const motifTrim = motifForce.trim();
      if (motifTrim.length < MOTIF_MIN_LENGTH) {
        setMotifErreur(
          `Motif obligatoire (${MOTIF_MIN_LENGTH} caractères minimum) pour tracer le forçage commercial.`,
        );
        return;
      }
    }
    setMotifErreur(null);

    // Recalcul final + propagation au store avant passage chiffrage.
    // Le calcul est idempotent côté backend (preview), pas d'effet de bord.
    const req = buildRequest();
    if (req === null) {
      setCalculError(
        "Renseignez Ø max bobine et vérifiez la quantité totale avant de continuer.",
      );
      return;
    }
    setCalculLoading(true);
    setCalculError(null);
    try {
      const res = await postRebobinageCalculer(req);
      setResult(res);
      // Propage au store → OptimisationChiffrage appliquera la ligne
      // sur le devis via applyRebobinageDevis après création/update.
      setRebobinage(req, res);
      goChiffrage();
    } catch (err) {
      setCalculError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setCalculLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-2xl font-bold">Rebobinage</h1>
        <p className="text-sm text-muted-foreground sm:text-base">
          Paramètres bobines client, calcul auto et arbitrage pré-coupé /
          découpe interne. Le commercial peut forcer un mode avec motif
          obligatoire (≥{MOTIF_MIN_LENGTH} caractères).
        </p>
      </header>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Sprint 16 — Sélecteur client : alimente l'auto-remplissage   */}
      {/* des paramètres bobine + propage `client_id` au devis final. */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card data-testid="client-section">
        <CardHeader>
          <CardTitle>Client du devis</CardTitle>
          <CardDescription>
            Le profil rebobinage du client sélectionné pré-remplit les
            paramètres bobine ci-dessous. Override possible à la main.
            Le client est aussi propagé à l&apos;étape chiffrage finale.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {clientsLoading && (
            <p className="text-sm text-muted-foreground">
              Chargement des clients…
            </p>
          )}
          {!clientsLoading && clientsError && (
            <div
              role="alert"
              data-testid="clients-erreur"
              className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
            >
              Chargement impossible : {clientsError}
            </div>
          )}
          {!clientsLoading && !clientsError && (
            <div className="space-y-2">
              <Label htmlFor="rebob-client">Client</Label>
              <select
                id="rebob-client"
                data-testid="client-select"
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={clientSelectionne?.id ?? ""}
                onChange={(e) => {
                  const id = e.target.value
                    ? Number(e.target.value)
                    : null;
                  const next = id !== null
                    ? clients.find((c) => c.id === id) ?? null
                    : null;
                  setClientSelectionne(next);
                }}
              >
                <option value="">— Aucun client sélectionné —</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.raison_sociale}
                  </option>
                ))}
              </select>
              {clientSelectionne && (
                <ClientExigencesBandeau client={clientSelectionne} />
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Rebobineuse — sélection scopée tenant (fin du hardcode id=1) */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card data-testid="rebobineuse-section">
        <CardHeader>
          <CardTitle>Rebobineuse</CardTitle>
          <CardDescription>
            Machine du parc qui exécutera le rebobinage. Le calcul de
            temps et de coût utilise sa vitesse pratique et son coût
            horaire.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {rebobineusesLoading && (
            <p className="text-sm text-muted-foreground">
              Chargement des rebobineuses du parc…
            </p>
          )}
          {!rebobineusesLoading && rebobineusesError && (
            <div
              role="alert"
              data-testid="rebobineuses-erreur"
              className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
            >
              Chargement impossible : {rebobineusesError}
            </div>
          )}
          {!rebobineusesLoading &&
            !rebobineusesError &&
            rebobineuses.length === 0 && (
              <div
                role="alert"
                data-testid="aucune-rebobineuse"
                className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
              >
                Aucune rebobineuse configurée pour ce tenant. Le calcul
                rebobinage n&apos;est pas disponible. Configurez au moins
                une rebobineuse dans le parc avant de continuer.
              </div>
            )}
          {!rebobineusesLoading &&
            !rebobineusesError &&
            rebobineuses.length === 1 && (
              <div
                data-testid="rebobineuse-unique"
                className="rounded-md border border-border bg-muted/30 p-3 text-sm"
              >
                Rebobineuse utilisée :{" "}
                <strong>{rebobineuses[0]!.nom}</strong>
                {!rebobineuses[0]!.actif && (
                  <span className="ml-2 rounded bg-gray-200 px-2 py-0.5 text-xs text-gray-700">
                    Désactivée
                  </span>
                )}
              </div>
            )}
          {!rebobineusesLoading &&
            !rebobineusesError &&
            rebobineuses.length > 1 && (
              <div className="space-y-2">
                <Label htmlFor="rebob-machine">Rebobineuse du parc</Label>
                <select
                  id="rebob-machine"
                  data-testid="rebobineuse-select"
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={machineRebobineuseId ?? ""}
                  onChange={(e) =>
                    setMachineRebobineuseId(Number(e.target.value))
                  }
                >
                  {rebobineuses.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.nom}
                      {!r.actif ? " (désactivée)" : ""}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  Le calcul se recalcule automatiquement au changement
                  de machine.
                </p>
              </div>
            )}
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Paramètres bobine client (pré-remplis)                      */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Paramètres bobines client</CardTitle>
          <CardDescription>
            Pré-remplis depuis le brief client + saisie initiale. Ajustez si
            le commercial a validé d&apos;autres valeurs avec ce client.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="rebob-mandrin">Ø Mandrin bobine (mm)</Label>
              <select
                id="rebob-mandrin"
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={diametreMandrin}
                onChange={(e) => setDiametreMandrin(Number(e.target.value))}
              >
                {DIAMETRES_MANDRIN_MM.map((d) => (
                  <option key={d} value={d}>
                    {d} mm
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                Pré-rempli depuis la saisie étape 1. Standard flexo : 40 ou
                76 mm.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rebob-diam-max">
                Ø Max bobine livrée (mm)
              </Label>
              <Input
                id="rebob-diam-max"
                type="number"
                min={50}
                max={600}
                step={1}
                value={diametreMaxBobine}
                onChange={(e) => setDiametreMaxBobine(e.target.value)}
                placeholder="ex: 300"
              />
              <p className="text-xs text-muted-foreground">
                Pré-rempli depuis le brief client. Requis pour le calcul.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rebob-nb-etiq">
                Nb étiquettes / bobine (optionnel)
              </Label>
              <Input
                id="rebob-nb-etiq"
                type="number"
                min={1}
                step={1}
                value={nbEtiqParBobine}
                onChange={(e) => setNbEtiqParBobine(e.target.value)}
                placeholder="laisser vide pour optimisation auto"
              />
              <p className="text-xs text-muted-foreground">
                Pré-rempli depuis le profil client / le brief. Si vide,
                le moteur calcule le nombre optimal pour saturer le Ø
                max bobine.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rebob-sens-enroulement">
                Sens d&apos;enroulement (1..8)
              </Label>
              <Input
                id="rebob-sens-enroulement"
                data-testid="sens-enroulement-input"
                type="number"
                min={1}
                max={8}
                step={1}
                value={sensEnroulementClient ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === "") {
                    setSensEnroulementClient(null);
                    return;
                  }
                  const n = parseInt(v, 10);
                  setSensEnroulementClient(
                    Number.isFinite(n) ? n : null,
                  );
                }}
                placeholder="ex: 3"
              />
              <p className="text-xs text-muted-foreground">
                Pré-rempli depuis le profil client. Stockage brut
                (convention SE1-SE8) ; aucune logique de rotation appliquée
                ici. Propagé dans le devis pour traçabilité.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Tarifs mandrins (saisie tenant)                             */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Tarifs mandrins</CardTitle>
          <CardDescription>
            Prix d&apos;achat des mandrins selon le mode. Defaults projet
            tant qu&apos;un catalogue tenant n&apos;est pas dispo — ajustez
            si vos tarifs fournisseurs sont différents.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="rebob-prix-precoupe">Pré-coupé (€/mandrin)</Label>
            <Input
              id="rebob-prix-precoupe"
              type="number"
              min={0}
              step={0.01}
              value={prixPreCoupe}
              onChange={(e) => setPrixPreCoupe(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rebob-cout-decoupe">
              Découpe interne (€/mandrin)
            </Label>
            <Input
              id="rebob-cout-decoupe"
              type="number"
              min={0}
              step={0.01}
              value={coutDecoupeInterne}
              onChange={(e) => setCoutDecoupeInterne(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rebob-cout-fixe">Coût fixe découpe (€)</Label>
            <Input
              id="rebob-cout-fixe"
              type="number"
              min={0}
              step={0.01}
              value={coutFixeDecoupeInterne}
              onChange={(e) => setCoutFixeDecoupeInterne(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Calcul auto + arbitrage                                     */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card data-testid="calcul-section">
        <CardHeader>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <CardTitle>Calcul rebobinage</CardTitle>
              <CardDescription>
                Sur la base de {nbEtiquettesTotal.toLocaleString("fr-FR")}{" "}
                étiquettes · intervalle dév {intervalleDevMm} mm · épaisseur{" "}
                {epaisseurMatiereUm} µm.
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void calculer()}
              disabled={calculLoading}
              data-testid="rebobinage-recalculer"
            >
              {calculLoading ? "Calcul…" : "Recalculer"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {calculError && (
            <div
              role="alert"
              data-testid="calcul-erreur"
              className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
            >
              {calculError}
            </div>
          )}

          {result ? (
            <>
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <KPI
                  label="Nombre de bobines"
                  value={result.bobines.nb_bobines.toLocaleString("fr-FR")}
                  testId="calcul-nb-bobines"
                />
                <KPI
                  label="Temps total"
                  value={`${formaterDecimal(result.temps.temps_total_min)} min`}
                  testId="calcul-temps"
                />
                <KPI
                  label="Coût total rebobinage"
                  value={formaterEuros(result.cout_total_rebobinage_eur)}
                  testId="calcul-cout"
                />
              </dl>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <ModeArbitrageCard
                  mode={result.arbitrage.mode_applique}
                  recommande={
                    result.arbitrage.mode_applique ===
                    result.arbitrage.mode_optimal
                  }
                  coutEur={
                    result.arbitrage.mode_applique === "pre_coupe"
                      ? result.arbitrage.cout_pre_coupe_total_eur
                      : result.arbitrage.cout_decoupe_interne_total_eur
                  }
                  testId="arbitrage-applique"
                />
                <ModeArbitrageCard
                  mode={
                    result.arbitrage.mode_applique === "pre_coupe"
                      ? "decoupe_interne"
                      : "pre_coupe"
                  }
                  recommande={false}
                  coutEur={
                    result.arbitrage.mode_applique === "pre_coupe"
                      ? result.arbitrage.cout_decoupe_interne_total_eur
                      : result.arbitrage.cout_pre_coupe_total_eur
                  }
                  ecartPct={result.arbitrage.ecart_pct}
                  testId="arbitrage-alternatif"
                />
              </div>
            </>
          ) : (
            !calculError && (
              <p className="text-sm text-muted-foreground">
                Renseignez les paramètres puis cliquez « Recalculer ».
              </p>
            )
          )}
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Souveraineté commerciale : forçage + motif obligatoire      */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card data-testid="forcage-section">
        <CardHeader>
          <CardTitle>Souveraineté commerciale</CardTitle>
          <CardDescription>
            Le commercial peut écraser la recommandation moteur. Le mode
            forcé et le motif sont tracés sur le devis.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={forcerMode}
              onChange={(e) => {
                setForcerMode(e.target.checked);
                if (!e.target.checked) {
                  setMotifErreur(null);
                }
              }}
              className="h-4 w-4 cursor-pointer accent-foreground"
              data-testid="forcer-mode-checkbox"
            />
            Forcer un mode (écrase la recommandation moteur)
          </label>
          {forcerMode && (
            <div className="space-y-3 rounded-md border border-amber-300 bg-amber-50 p-4">
              <div className="space-y-2">
                <Label htmlFor="rebob-mode-force">Mode forcé</Label>
                <select
                  id="rebob-mode-force"
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={modeForce}
                  onChange={(e) =>
                    setModeForce(e.target.value as ModeRebobinageApplique)
                  }
                >
                  <option value="pre_coupe">{MODE_LABEL.pre_coupe}</option>
                  <option value="decoupe_interne">
                    {MODE_LABEL.decoupe_interne}
                  </option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="rebob-motif-force">
                  Motif du forçage (obligatoire,{" "}
                  {MOTIF_MIN_LENGTH} caractères minimum)
                </Label>
                <textarea
                  id="rebob-motif-force"
                  data-testid="motif-force-textarea"
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  rows={3}
                  value={motifForce}
                  onChange={(e) => {
                    setMotifForce(e.target.value);
                    if (motifErreur) setMotifErreur(null);
                  }}
                  placeholder="Contrainte client, urgence, capacité atelier saturée…"
                />
                <p className="text-xs text-muted-foreground">
                  Le motif est persisté avec la décision sur le devis pour
                  traçabilité.
                </p>
              </div>
              {motifErreur && (
                <div
                  role="alert"
                  data-testid="motif-erreur"
                  className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
                >
                  {motifErreur}
                </div>
              )}
            </div>
          )}

          <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
            <strong>Mode retenu :</strong>{" "}
            <span data-testid="mode-retenu">
              {MODE_LABEL[modeRetenuFinal]}
            </span>{" "}
            {forcerMode ? (
              <span className="text-amber-800">(forcé commercial)</span>
            ) : (
              <span className="text-muted-foreground">
                (recommandation moteur)
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Navigation                                                  */}
      {/* ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <Button variant="outline" size="sm" onClick={goDetail}>
          ← Retour détail lots
        </Button>
        <Button
          size="lg"
          onClick={() => void validerEtContinuer()}
          disabled={
            calculLoading ||
            machineRebobineuseId === null ||
            rebobineuses.length === 0
          }
          data-testid="rebobinage-continuer"
          className="bg-gradient-to-r from-blue-700 to-amber-600 px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:from-blue-800 hover:to-amber-700 hover:shadow-lg disabled:opacity-50"
        >
          {calculLoading
            ? "Calcul en cours…"
            : "Continuer vers chiffrage →"}
        </Button>
      </div>
    </main>
  );
}

// ──────────────────────────────────────────────────────────────────
// Helpers d'affichage
// ──────────────────────────────────────────────────────────────────

function formaterDecimal(str: string): string {
  const n = parseFloat(str);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function formaterEuros(str: string): string {
  const n = parseFloat(str);
  if (!Number.isFinite(n)) return "—";
  return `${n.toLocaleString("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} €`;
}

// ──────────────────────────────────────────────────────────────────
// Sous-composants
// ──────────────────────────────────────────────────────────────────

function KPI({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-muted/20 p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div
        data-testid={testId}
        className="mt-1 font-mono text-2xl font-semibold text-foreground"
      >
        {value}
      </div>
    </div>
  );
}

function ModeArbitrageCard({
  mode,
  recommande,
  coutEur,
  ecartPct,
  testId,
}: {
  mode: ModeRebobinageApplique;
  recommande: boolean;
  coutEur: string;
  ecartPct?: string;
  testId?: string;
}) {
  const ecartNumber = ecartPct !== undefined ? parseFloat(ecartPct) : null;
  return (
    <div
      data-testid={testId}
      className={cn(
        "rounded-md border-2 p-4",
        recommande
          ? "border-emerald-400 bg-emerald-50"
          : "border-border bg-background",
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-base font-semibold">{MODE_LABEL[mode]}</div>
        {recommande ? (
          <span className="rounded bg-emerald-600 px-2 py-0.5 text-xs font-semibold text-white">
            Appliqué
          </span>
        ) : (
          <span className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700">
            Alternatif
          </span>
        )}
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {MODE_DESCRIPTION[mode]}
      </p>
      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm">
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            Coût (mandrins + machine)
          </dt>
          <dd className="font-mono font-semibold">{formaterEuros(coutEur)}</dd>
        </div>
      </dl>
      {ecartNumber !== null && ecartNumber !== 0 && (
        <div className="mt-2 text-xs text-amber-800">
          Écart vs appliqué :{" "}
          <strong>
            {ecartNumber > 0 ? "+" : ""}
            {ecartNumber.toLocaleString("fr-FR", {
              maximumFractionDigits: 1,
            })}{" "}
            %
          </strong>
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Bandeau "Exigences client" (Sprint 16 auto-fill — Q2 tranchée).
// Affiche en read-only les 5 champs profil non-consommés par le moteur
// de calcul rebobinage : 3 booléens (uniquement si true) + 2 textes
// (uniquement si renseignés). Si rien à montrer → pas de bandeau.
// L'édition se fait sur la fiche client, pas ici.
// ──────────────────────────────────────────────────────────────────
function ClientExigencesBandeau({
  client,
}: {
  client: import("@/lib/api").Client;
}) {
  const exigencesBool: { label: string; testId: string }[] = [];
  if (client.marquage_bobine_requis) {
    exigencesBool.push({
      label: "Marquage bobine requis",
      testId: "exigence-marquage",
    });
  }
  if (client.mandrin_fourni_par_client) {
    exigencesBool.push({
      label: "Mandrin fourni par le client",
      testId: "exigence-mandrin",
    });
  }
  if (client.film_protection_requis) {
    exigencesBool.push({
      label: "Film protection requis",
      testId: "exigence-film",
    });
  }

  const aQuelqueChose =
    exigencesBool.length > 0 ||
    (client.marquage_bobine_format !== null &&
      client.marquage_bobine_format.length > 0) ||
    (client.conditionnement_souhaite !== null &&
      client.conditionnement_souhaite.length > 0);

  if (!aQuelqueChose) return null;

  return (
    <div
      data-testid="exigences-client-bandeau"
      className="mt-3 space-y-2 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900"
    >
      <div className="text-xs font-semibold uppercase tracking-wide">
        Exigences client (édition sur la fiche client)
      </div>
      {exigencesBool.length > 0 && (
        <ul className="space-y-1">
          {exigencesBool.map((e) => (
            <li key={e.testId} data-testid={e.testId}>
              ☑ {e.label}
            </li>
          ))}
        </ul>
      )}
      {client.marquage_bobine_format && (
        <div data-testid="exigence-marquage-format">
          <span className="font-medium">Format du marquage :</span>{" "}
          {client.marquage_bobine_format}
        </div>
      )}
      {client.conditionnement_souhaite && (
        <div data-testid="exigence-conditionnement">
          <span className="font-medium">Conditionnement souhaité :</span>{" "}
          {client.conditionnement_souhaite}
        </div>
      )}
    </div>
  );
}
