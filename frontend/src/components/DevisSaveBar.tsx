"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  ApiError,
  createDevis,
  listClients,
  updateDevis,
  type Client,
  type DevisCalculResult,
  type DevisInput,
  type DevisStatut,
} from "@/lib/api";

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

interface DevisSaveBarProps {
  input: DevisInput;
  result: DevisCalculResult;
  // Mode 'create' = POST → redirect /devis/{id}
  // Mode 'edit'   = PUT /api/devis/{devisId} → redirect /devis/{devisId}
  mode: "create" | "edit";
  devisId?: number;
  initialClientId?: number | null;
  initialStatut?: DevisStatut;
  initialCylindreZ?: number | null;
  initialCylindreNbEtiq?: number | null;
  onSaved: (newDevisId: number) => void;
}

export function DevisSaveBar({
  input,
  result,
  mode,
  devisId,
  initialClientId,
  initialStatut,
  initialCylindreZ,
  initialCylindreNbEtiq,
  onSaved,
}: DevisSaveBarProps) {
  const { toast } = useToast();
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState<number | null>(
    initialClientId ?? null
  );
  const [statut, setStatut] = useState<DevisStatut>(
    initialStatut ?? "brouillon"
  );
  // En mode matching : index du candidat sélectionné dans result.candidats.
  // Pré-rempli depuis initialCylindreZ si on édite un devis matching existant.
  const [selectedCandidatIdx, setSelectedCandidatIdx] = useState<number | null>(
    () => {
      if (result.mode !== "matching" || initialCylindreZ == null) return null;
      const idx = result.candidats.findIndex(
        (c) =>
          c.z === initialCylindreZ &&
          c.nb_etiq_par_tour === (initialCylindreNbEtiq ?? c.nb_etiq_par_tour)
      );
      return idx >= 0 ? idx : null;
    }
  );
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    listClients()
      .then(setClients)
      .catch(() => setClients([]));
  }, []);

  const matchingNeedsCylindre =
    result.mode === "matching" && selectedCandidatIdx === null;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      let cylindre_z: number | null = null;
      let cylindre_nb_etiq: number | null = null;
      if (result.mode === "matching" && selectedCandidatIdx !== null) {
        const c = result.candidats[selectedCandidatIdx];
        cylindre_z = c.z;
        cylindre_nb_etiq = c.nb_etiq_par_tour;
      }

      if (mode === "create") {
        const created = await createDevis({
          payload_input: input as unknown as Record<string, unknown>,
          payload_output: result as unknown as Record<string, unknown>,
          client_id: clientId,
          statut,
          cylindre_choisi_z: cylindre_z,
          cylindre_choisi_nb_etiq: cylindre_nb_etiq,
        });
        toast({
          title: "Devis sauvegardé",
          description: `Numéro ${created.numero}`,
        });
        onSaved(created.id);
      } else {
        if (devisId == null) throw new Error("devisId manquant en mode edit");
        const updated = await updateDevis(devisId, {
          payload_input: input as unknown as Record<string, unknown>,
          payload_output: result as unknown as Record<string, unknown>,
          client_id: clientId,
          statut,
          cylindre_choisi_z: cylindre_z,
          cylindre_choisi_nb_etiq: cylindre_nb_etiq,
        });
        toast({
          title: "Devis mis à jour",
          description: `Numéro ${updated.numero}`,
        });
        onSaved(updated.id);
      }
    } catch (err) {
      toast({
        title: "Erreur sauvegarde",
        description:
          err instanceof ApiError
            ? err.message.split(" → ").pop() ?? err.message
            : err instanceof Error
              ? err.message
              : "Erreur inconnue",
        variant: "destructive",
      });
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {mode === "create"
            ? "Sauvegarder ce devis"
            : "Mettre à jour ce devis"}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="save-client">Client (optionnel)</Label>
            <select
              id="save-client"
              className={selectClass}
              value={clientId ?? ""}
              onChange={(e) =>
                setClientId(e.target.value ? Number(e.target.value) : null)
              }
            >
              <option value="">— Aucun —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.raison_sociale}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="save-statut">Statut</Label>
            <select
              id="save-statut"
              className={selectClass}
              value={statut}
              onChange={(e) => setStatut(e.target.value as DevisStatut)}
            >
              <option value="brouillon">Brouillon</option>
              <option value="valide">Valide</option>
            </select>
          </div>
        </div>

        {result.mode === "matching" && (
          <div className="grid gap-2">
            <Label>
              Cylindre à utiliser (sélection obligatoire avant sauvegarde)
            </Label>
            <div className="grid gap-2">
              {result.candidats.map((c, idx) => (
                <label
                  key={`${c.z}-${c.nb_etiq_par_tour}`}
                  className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 text-sm ${
                    selectedCandidatIdx === idx
                      ? "border-primary bg-primary/5"
                      : ""
                  }`}
                >
                  <input
                    type="radio"
                    name="cylindre-choisi"
                    checked={selectedCandidatIdx === idx}
                    onChange={() => setSelectedCandidatIdx(idx)}
                  />
                  <span className="flex-1">
                    <strong>
                      Z={c.z}, {c.nb_etiq_par_tour} étiq/tour
                    </strong>{" "}
                    · intervalle {parseFloat(c.intervalle_mm).toFixed(2)} mm ·
                    prix au mille{" "}
                    <span className="font-mono">
                      {parseFloat(c.prix_au_mille_eur).toFixed(2)} €
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={isSaving || matchingNeedsCylindre}
            title={
              matchingNeedsCylindre
                ? "Sélectionnez un cylindre avant de sauvegarder"
                : undefined
            }
          >
            {isSaving
              ? "Sauvegarde…"
              : mode === "create"
                ? "💾 Sauvegarder ce devis"
                : "💾 Mettre à jour"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
