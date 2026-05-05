"use client";

import { useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { ApiError, deleteAdminUser } from "@/lib/api";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import type { AdminUser } from "@/types/admin";

interface Props {
  target: AdminUser | null;
  onClose: () => void;
  onDeleted: () => void | Promise<void>;
}

export function DeleteUserDialog({ target, onClose, onDeleted }: Props) {
  const { toast } = useToast();
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!target) return;
    // On gère manuellement la fermeture pour éviter qu'AlertDialogAction
    // ne ferme la dialog avant la fin de la requête. preventDefault ici
    // empêche le close auto de Radix.
    e.preventDefault();
    setSubmitting(true);
    try {
      await deleteAdminUser(target.id);
      toast({
        title: "Compte supprimé",
        description: `${target.email} et toutes les données associées.`,
      });
      onClose();
      await onDeleted();
    } catch (err) {
      toast({
        title: "Suppression impossible",
        description:
          err instanceof ApiError || err instanceof Error
            ? err.message
            : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AlertDialog
      open={target !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Supprimer ce compte ?</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>
                Cette action est <strong className="text-foreground">irréversible</strong>.
                Toutes les données associées (devis, machines, tarifs, clients,
                etc.) seront définitivement supprimées via CASCADE.
              </p>
              {target && (
                <div className="rounded-md border bg-muted/40 p-3 text-foreground">
                  <div>
                    <span className="font-medium">Compte&nbsp;:</span>{" "}
                    {target.email}
                  </div>
                  <div>
                    <span className="font-medium">Entreprise&nbsp;:</span>{" "}
                    {target.nom_entreprise}
                  </div>
                </div>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={submitting}>Annuler</AlertDialogCancel>
          <AlertDialogAction
            disabled={submitting}
            onClick={handleConfirm}
            className={cn(
              buttonVariants({ variant: "destructive" }),
              "mt-2 sm:mt-0"
            )}
          >
            {submitting ? "Suppression…" : "Supprimer définitivement"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
