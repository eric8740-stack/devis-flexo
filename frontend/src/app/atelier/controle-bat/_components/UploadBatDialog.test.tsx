import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { UploadBatDialog } from "./UploadBatDialog";

// Sprint 15 Lot B — tests RTL du dialog d'upload BAT.
// Mocke directement uploadBatReference depuis le client API.

const uploadMock = vi.fn();
vi.mock("@/lib/api/controleBat", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/api/controleBat")>();
  return {
    ...actual,
    uploadBatReference: (...args: Parameters<typeof actual.uploadBatReference>) =>
      uploadMock(...args),
  };
});

function renderDialog(
  overrides: Partial<{
    open: boolean;
    onOpenChange: (b: boolean) => void;
    onUploaded: () => void;
  }> = {},
) {
  const onOpenChange = overrides.onOpenChange ?? vi.fn();
  const onUploaded = overrides.onUploaded ?? vi.fn();
  const open = overrides.open ?? true;
  render(
    <UploadBatDialog
      devisId={42}
      devisNumero="DEV-2026-0042"
      open={open}
      onOpenChange={onOpenChange}
      onUploaded={onUploaded}
    />,
  );
  return { onOpenChange, onUploaded };
}

describe("UploadBatDialog — Lot B", () => {
  beforeEach(() => {
    uploadMock.mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("titre + description visible avec le numéro du devis", () => {
    renderDialog();
    expect(
      screen.getByText(/Rattacher le BAT — DEV-2026-0042/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/PDF, JPEG, PNG, WebP/i),
    ).toBeInTheDocument();
  });

  it("bouton téléverser désactivé tant qu'aucun fichier valide n'est sélectionné", () => {
    renderDialog();
    const submit = screen.getByRole("button", { name: /Téléverser le BAT/i });
    expect(submit).toBeDisabled();
  });

  it("sélection PDF via input : preview badge fichier, bouton activé", async () => {
    renderDialog();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const pdf = new File(["%PDF"], "bat.pdf", { type: "application/pdf" });
    await userEvent.upload(input, pdf);

    expect(screen.getByTestId("file-preview")).toHaveTextContent("bat.pdf");
    expect(
      screen.getByText(/Aperçu PDF non disponible/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Téléverser le BAT/i }),
    ).toBeEnabled();
  });

  it("sélection image PNG : aperçu inline (balise img)", async () => {
    renderDialog();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const png = new File(["89PNG"], "photo.png", { type: "image/png" });
    await userEvent.upload(input, png);

    const preview = screen.getByTestId("file-preview");
    expect(preview).toHaveTextContent("photo.png");
    expect(preview.querySelector("img")).not.toBeNull();
  });

  it("type non supporté : erreur affichée en role=alert, fichier non retenu", async () => {
    renderDialog();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const txt = new File(["hello"], "notes.txt", { type: "text/plain" });
    // applyAccept:false → userEvent ne filtre pas sur l'attribut accept de
    // l'input ; on veut tester la validation runtime, pas le filtre HTML.
    await userEvent.upload(input, txt, { applyAccept: false });

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Format non supporté/i);
    expect(screen.queryByTestId("file-preview")).toBeNull();
    expect(
      screen.getByRole("button", { name: /Téléverser le BAT/i }),
    ).toBeDisabled();
  });

  it("fichier trop volumineux : erreur affichée, fichier non retenu", async () => {
    renderDialog();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    // 11 Mo > BAT_MAX_SIZE_MO (10)
    const big = new File([new Uint8Array(11 * 1024 * 1024)], "big.pdf", {
      type: "application/pdf",
    });
    await userEvent.upload(input, big);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/trop volumineux/i);
    expect(screen.queryByTestId("file-preview")).toBeNull();
  });

  it("submit happy path : appel uploadBatReference + onUploaded + fermeture", async () => {
    uploadMock.mockResolvedValueOnce({
      devis_id: 42,
      bat_filename: "bat.pdf",
      bat_mime_type: "application/pdf",
      bat_uploaded_at: "2026-05-24T10:00:00",
    });

    const { onUploaded, onOpenChange } = renderDialog();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const pdf = new File(["%PDF"], "bat.pdf", { type: "application/pdf" });
    await userEvent.upload(input, pdf);
    await userEvent.click(
      screen.getByRole("button", { name: /Téléverser le BAT/i }),
    );

    await waitFor(() => expect(uploadMock).toHaveBeenCalledTimes(1));
    expect(uploadMock).toHaveBeenCalledWith(42, pdf);
    expect(onUploaded).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("erreur upload : message dans alert, dialog reste ouvert, pas de onUploaded", async () => {
    uploadMock.mockRejectedValueOnce(new Error("POST → 422 Devis introuvable"));

    const { onUploaded, onOpenChange } = renderDialog();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const pdf = new File(["%PDF"], "bat.pdf", { type: "application/pdf" });
    await userEvent.upload(input, pdf);
    await userEvent.click(
      screen.getByRole("button", { name: /Téléverser le BAT/i }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Devis introuvable/);
    expect(onUploaded).not.toHaveBeenCalled();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
