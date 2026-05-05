"use client";

import { useState } from "react";

import { DeleteUserDialog } from "@/components/admin/DeleteUserDialog";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { ApiError, disableAdminUser, enableAdminUser } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AdminUser } from "@/types/admin";

interface Props {
  users: AdminUser[];
  onChange: () => void | Promise<void>;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function Badge({
  children,
  tone,
  title,
}: {
  children: React.ReactNode;
  tone: "primary" | "success" | "muted" | "warning";
  title?: string;
}) {
  const cls = {
    primary: "bg-primary/10 text-primary border-primary/20",
    success: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
    muted: "bg-muted text-muted-foreground border-border",
    warning: "bg-amber-500/10 text-amber-700 border-amber-500/20",
  }[tone];
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        cls
      )}
    >
      {children}
    </span>
  );
}

export function AdminUserTable({ users, onChange }: Props) {
  const { user: connectedUser } = useAuth();
  const { toast } = useToast();
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);

  const handleToggle = async (target: AdminUser) => {
    setPendingId(target.id);
    try {
      if (target.is_active) {
        await disableAdminUser(target.id);
        toast({
          title: "Compte désactivé",
          description: target.email,
        });
      } else {
        await enableAdminUser(target.id);
        toast({
          title: "Compte réactivé",
          description: target.email,
        });
      }
      await onChange();
    } catch (err) {
      toast({
        title: "Action impossible",
        description:
          err instanceof ApiError || err instanceof Error
            ? err.message
            : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setPendingId(null);
    }
  };

  return (
    <>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Entreprise</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>Rôle</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Créé le</TableHead>
              <TableHead>Dernière connexion</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center text-muted-foreground"
                >
                  Aucun compte enregistré.
                </TableCell>
              </TableRow>
            )}
            {users.map((u) => {
              const isSelf = connectedUser?.id === u.id;
              const isBusy = pendingId === u.id;
              return (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.email}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span>{u.nom_entreprise}</span>
                      {u.is_demo && <Badge tone="primary">Demo</Badge>}
                    </div>
                  </TableCell>
                  <TableCell>{u.nom_contact}</TableCell>
                  <TableCell>
                    {u.is_admin ? (
                      <Badge tone="warning">Admin</Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">User</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {u.is_active ? (
                      <Badge tone="success">Actif</Badge>
                    ) : (
                      <Badge tone="muted">Inactif</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(u.date_creation)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {u.date_derniere_connexion
                      ? formatDate(u.date_derniere_connexion)
                      : "Jamais"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isBusy || isSelf}
                        onClick={() => handleToggle(u)}
                        title={
                          isSelf
                            ? "Vous ne pouvez pas désactiver votre propre compte"
                            : u.is_active
                              ? "Désactiver le compte"
                              : "Réactiver le compte"
                        }
                      >
                        {u.is_active ? "Désactiver" : "Réactiver"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-destructive/40 text-destructive hover:bg-destructive/10"
                        disabled={isBusy || isSelf || u.is_demo}
                        onClick={() => setDeleteTarget(u)}
                        title={
                          isSelf
                            ? "Vous ne pouvez pas supprimer votre propre compte"
                            : u.is_demo
                              ? "Compte démo, non supprimable"
                              : "Supprimer définitivement"
                        }
                      >
                        Supprimer
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <DeleteUserDialog
        target={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onDeleted={onChange}
      />
    </>
  );
}
