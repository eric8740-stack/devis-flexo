"use client";

/**
 * Stock S3 — consommer le stock depuis un devis enregistré (contrat figé).
 * Proposition FIFO ajustable (ml par bobine, inclure/exclure) · bandeau si
 * stock insuffisant (non bloquant) · consommation transactionnelle (409 géré)
 * · annulation. Front pur (le back pilote FIFO + transaction). Dégradation
 * propre si back S3 absent : le bloc ne s'affiche pas (pas de crash).
 *
 * ⚠️ Limite contrat : pas de moyen de détecter « déjà consommé » au RECHARGEMENT
 * (pas de filtre devis_id sur /api/mouvements ni de champ sur le devis). L'état
 * « consommé » + Annuler est donc géré IN-SESSION (après la consommation).
 */
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import {
  ApiError,
  annulerConsommation,
  consommerStock,
  getPropositionConsommation,
  type ConsommationResult,
  type PropositionConsommation,
} from "@/lib/api";

interface Ligne {
  bobine_id: number;
  emplacement: string;
  laize_mm: number;
  ml_restant: number;
  ml: string;
  included: boolean;
}

const mlFr = (n: number) =>
  n.toLocaleString("fr-FR", { maximumFractionDigits: 0 });

export function ConsommationStock({ devisId }: { devisId: number }) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [indispo, setIndispo] = useState(false); // back S3 absent → masqué
  const [prop, setProp] = useState<PropositionConsommation | null>(null);
  const [lignes, setLignes] = useState<Ligne[]>([]);
  const [consuming, setConsuming] = useState(false);
  const [result, setResult] = useState<ConsommationResult | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const p = await getPropositionConsommation(devisId);
      setProp(p);
      setLignes(
        p.lignes.map((l) => ({
          bobine_id: l.bobine_id,
          emplacement: l.emplacement,
          laize_mm: l.laize_mm,
          ml_restant: l.ml_restant,
          ml: String(l.ml_propose),
          included: true,
        })),
      );
      setIndispo(false);
    } catch {
      // Dégradation propre : back S3 absent → on masque le bloc.
      setIndispo(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [devisId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (indispo || (loading && prop === null)) return null;
  if (prop === null) return null;

  const totalSelect = lignes
    .filter((l) => l.included)
    .reduce((s, l) => s + (parseFloat(l.ml) || 0), 0);
  const insuffisant = !prop.stock_suffisant || totalSelect < prop.ml_requis;
  const manque = prop.manque_ml || Math.max(0, prop.ml_requis - totalSelect);

  // Vue « consommé » : in-session (result) OU persisté (proposition, gap #4).
  const estConsomme = result !== null || prop.deja_consomme;
  const consommeMvts = result ? result.mouvements : prop.mouvements;
  const consommeMl = result
    ? result.mouvements.reduce((s, m) => s + m.ml, 0)
    : prop.consomme_ml;

  const setLigne = (id: number, patch: Partial<Ligne>) =>
    setLignes((ls) => ls.map((l) => (l.bobine_id === id ? { ...l, ...patch } : l)));

  const consommer = async () => {
    // Le back attend `ml` entier (> 0) → on arrondit.
    const payload = lignes
      .filter((l) => l.included && parseFloat(l.ml) > 0)
      .map((l) => ({ bobine_id: l.bobine_id, ml: Math.round(parseFloat(l.ml)) }));
    if (payload.length === 0) return;
    setConsuming(true);
    try {
      const res = await consommerStock(devisId, payload);
      setResult(res);
      toast({ title: "Stock consommé ✓" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast({
          title: "Stock insuffisant",
          description:
            "Une ligne dépasse le ml restant de sa bobine — rien n'a été consommé.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Consommation impossible",
          description: err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      }
    } finally {
      setConsuming(false);
    }
  };

  const annuler = async () => {
    try {
      await annulerConsommation(devisId);
      setResult(null);
      toast({ title: "Consommation annulée ✓" });
      await load();
    } catch (err) {
      toast({
        title: "Annulation impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  return (
    <Card data-testid="consommation-stock" className="border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Consommer le stock</CardTitle>
      </CardHeader>
      <CardContent>
        {estConsomme ? (
          // ── Consommé (in-session OU persisté via deja_consomme) ─────
          <div data-testid="consomme-view" className="space-y-3 text-sm">
            <p className="rounded-md bg-emerald-50 px-3 py-2 text-emerald-800">
              Ce devis a consommé <strong>{mlFr(consommeMl)} ml</strong> depuis{" "}
              <strong>{consommeMvts.length}</strong> bobine(s).
            </p>
            <ul className="space-y-1">
              {consommeMvts.map((m) => (
                <li key={m.id} className="font-mono text-xs text-muted-foreground">
                  bobine #{m.bobine_id} · −{mlFr(m.ml)} ml
                </li>
              ))}
            </ul>
            <Button
              type="button"
              variant="ghost"
              onClick={annuler}
              data-testid="annuler-consommation"
            >
              Annuler la consommation
            </Button>
          </div>
        ) : (
          // ── Proposition FIFO ajustable ─────────────────────────────
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">
              Besoin matière : <strong>{mlFr(prop.ml_requis)} ml</strong> ·
              sélectionné{" "}
              <strong className="text-foreground">
                {mlFr(totalSelect)} ml
              </strong>
            </p>
            {insuffisant && (
              <div
                data-testid="manque-bandeau"
                className="rounded-md bg-amber-50 px-3 py-2 text-amber-800"
              >
                ⚠ Stock insuffisant — manque <strong>{mlFr(manque)} ml</strong>.
                Tu peux consommer ce qui est disponible (le reste à
                approvisionner).
              </div>
            )}
            {lignes.length === 0 ? (
              <p
                data-testid="aucune-bobine"
                className="text-muted-foreground"
              >
                Aucune bobine compatible en stock (matière + laize).
              </p>
            ) : (
              <ul className="space-y-2">
                {lignes.map((l) => (
                  <li
                    key={l.bobine_id}
                    data-testid={`conso-ligne-${l.bobine_id}`}
                    className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-border p-2"
                  >
                    <label className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-[#E85D2F]"
                        checked={l.included}
                        onChange={(e) =>
                          setLigne(l.bobine_id, { included: e.target.checked })
                        }
                        data-testid={`conso-inc-${l.bobine_id}`}
                      />
                      <span className="font-mono">{l.emplacement}</span>
                    </label>
                    <span className="text-xs text-muted-foreground">
                      laize {l.laize_mm} mm · reste {mlFr(l.ml_restant)} ml
                    </span>
                    <span className="ml-auto flex items-center gap-1">
                      <Input
                        type="number"
                        min={0}
                        max={l.ml_restant}
                        value={l.ml}
                        onChange={(e) =>
                          setLigne(l.bobine_id, { ml: e.target.value })
                        }
                        disabled={!l.included}
                        data-testid={`conso-ml-${l.bobine_id}`}
                        className="h-8 w-24"
                      />
                      <span className="text-xs text-muted-foreground">ml</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <Button
              type="button"
              onClick={consommer}
              disabled={consuming || totalSelect <= 0}
              data-testid="consommer"
              className="bg-[#E85D2F] text-white hover:bg-[#d24f24] disabled:opacity-50"
            >
              {consuming ? "Consommation…" : "Consommer le stock"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
