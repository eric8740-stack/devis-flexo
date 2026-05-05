"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminUserTable } from "@/components/admin/AdminUserTable";
import { CreateUserDialog } from "@/components/admin/CreateUserDialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { ApiError, listAdminUsers } from "@/lib/api";
import type { AdminUser } from "@/types/admin";

export default function AdminPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await listAdminUsers();
      setUsers(data);
    } catch (err) {
      toast({
        title: "Chargement échoué",
        description:
          err instanceof ApiError || err instanceof Error
            ? err.message
            : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  return (
    <main className="container mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Administration</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Gestion des comptes utilisateurs (réservé à l&apos;administrateur).
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>+ Nouveau compte</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Comptes utilisateurs ({users.length})</CardTitle>
          <CardDescription>
            Toutes les entreprises hébergées sur la plateforme. Les actions
            sont scopées par CASCADE sur l&apos;entreprise associée.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Chargement…
            </div>
          ) : (
            <AdminUserTable users={users} onChange={loadUsers} />
          )}
        </CardContent>
      </Card>

      <CreateUserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={loadUsers}
      />
    </main>
  );
}
