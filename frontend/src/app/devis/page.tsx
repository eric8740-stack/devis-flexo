"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  listDevis,
  type DevisListItem,
  type DevisListResponse,
  type DevisSort,
  type DevisStatut,
} from "@/lib/api";

const PER_PAGE = 25;

const fmtEur = (s: string) =>
  new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(parseFloat(s));

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

const STATUT_BADGE: Record<DevisStatut, string> = {
  brouillon: "bg-amber-100 text-amber-800",
  valide: "bg-emerald-100 text-emerald-800",
};

const selectClass =
  "flex h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export default function DevisListPage() {
  const [data, setData] = useState<DevisListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statut, setStatut] = useState<DevisStatut | "">("");
  const [sort, setSort] = useState<DevisSort>("date_desc");
  const [page, setPage] = useState(1);

  // Debounce 300ms sur la barre de recherche
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  // Reset page=1 quand on change recherche/filtre/tri
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statut, sort]);

  useEffect(() => {
    setError(null);
    listDevis({
      page,
      per_page: PER_PAGE,
      search: debouncedSearch || undefined,
      statut: statut || undefined,
      sort,
    })
      .then(setData)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [page, debouncedSearch, statut, sort]);

  return (
    <main className="container mx-auto max-w-6xl p-4 sm:p-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Devis</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Liste des devis sauvegardés. Tri par date décroissante par défaut.
          </p>
        </div>
        <Button asChild>
          <Link href="/devis/nouveau">+ Nouveau devis</Link>
        </Button>
      </header>

      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_180px_180px]">
        <div className="grid gap-2">
          <Label htmlFor="search">Recherche (numéro ou client)</Label>
          <Input
            id="search"
            type="search"
            placeholder="DEV-2026-0001 ou raison sociale…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="statut">Statut</Label>
          <select
            id="statut"
            className={selectClass}
            value={statut}
            onChange={(e) => setStatut(e.target.value as DevisStatut | "")}
          >
            <option value="">Tous</option>
            <option value="brouillon">Brouillon</option>
            <option value="valide">Valide</option>
          </select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="sort">Tri</Label>
          <select
            id="sort"
            className={selectClass}
            value={sort}
            onChange={(e) => setSort(e.target.value as DevisSort)}
          >
            <option value="date_desc">Date ↓ (récent)</option>
            <option value="date_asc">Date ↑ (ancien)</option>
            <option value="numero_asc">Numéro ↑</option>
            <option value="ht_desc">HT ↓ (gros montant)</option>
          </select>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive"
        >
          <strong>Erreur :</strong> {error}
        </div>
      )}

      {data && data.items.length === 0 && (
        <div className="rounded-md border border-dashed bg-muted/30 p-8 text-center text-sm text-muted-foreground">
          {debouncedSearch || statut
            ? "Aucun devis ne correspond aux filtres."
            : "Aucun devis pour le moment."}
          {!debouncedSearch && !statut && (
            <div className="mt-4">
              <Button asChild>
                <Link href="/devis/nouveau">Créer un devis</Link>
              </Button>
            </div>
          )}
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Numéro</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Machine</TableHead>
                  <TableHead className="text-right">HT</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((d: DevisListItem) => (
                  <TableRow key={d.id} className="hover:bg-muted/50">
                    <TableCell className="font-mono text-sm">
                      <Link
                        href={`/devis/${d.id}`}
                        className="text-primary hover:underline"
                      >
                        {d.numero}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm">
                      {fmtDate(d.date_creation)}
                    </TableCell>
                    <TableCell className="text-sm">
                      {d.client_nom ?? "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {parseFloat(d.format_l_mm)}×{parseFloat(d.format_h_mm)} mm
                    </TableCell>
                    <TableCell className="text-sm">{d.machine_nom}</TableCell>
                    <TableCell className="text-right font-mono">
                      {fmtEur(d.ht_total_eur)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${STATUT_BADGE[d.statut]}`}
                      >
                        {d.statut === "brouillon" ? "Brouillon" : "Valide"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/devis/${d.id}`}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        Voir →
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm">
            <div className="text-muted-foreground">
              {data.total} devis · page {data.page} / {data.pages}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ← Précédent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant →
              </Button>
            </div>
          </div>
        </>
      )}

      {!data && !error && (
        <div className="text-sm text-muted-foreground">Chargement…</div>
      )}
    </main>
  );
}
