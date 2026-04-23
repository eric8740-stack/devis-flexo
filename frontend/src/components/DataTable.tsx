"use client";

import type { ReactNode } from "react";
import { Pencil, Trash2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface Column<T> {
  key: string;
  label: string;
  render?: (item: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T extends { id: number }> {
  data: T[];
  columns: Column<T>[];
  onEdit?: (item: T) => void;
  onDelete?: (item: T) => void | Promise<void>;
  /** Texte affiché dans le dialog de confirmation de suppression. */
  deleteConfirmLabel?: (item: T) => string;
  emptyLabel?: string;
}

export function DataTable<T extends { id: number }>({
  data,
  columns,
  onEdit,
  onDelete,
  deleteConfirmLabel,
  emptyLabel = "Aucune donnée.",
}: DataTableProps<T>) {
  const hasActions = Boolean(onEdit || onDelete);

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        {emptyLabel}
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead key={col.key} className={col.className}>
              {col.label}
            </TableHead>
          ))}
          {hasActions && (
            <TableHead className="w-32 text-right">Actions</TableHead>
          )}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item) => (
          <TableRow key={item.id}>
            {columns.map((col) => (
              <TableCell key={col.key} className={col.className}>
                {col.render
                  ? col.render(item)
                  : formatCell(
                      (item as Record<string, unknown>)[col.key]
                    )}
              </TableCell>
            ))}
            {hasActions && (
              <TableCell className="space-x-1 text-right">
                {onEdit && (
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Éditer"
                    onClick={() => onEdit(item)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                )}
                {onDelete && (
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Supprimer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          Confirmer la suppression
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          {deleteConfirmLabel
                            ? deleteConfirmLabel(item)
                            : "Cette action est irréversible."}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Annuler</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => onDelete(item)}
                        >
                          Supprimer
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function formatCell(value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}
