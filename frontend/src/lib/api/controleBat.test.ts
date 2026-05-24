import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";

import {
  listProductionsActives,
  uploadBatReference,
  type ProductionActive,
} from "./controleBat";

// Sprint 15 Lot A — tests du client API isolé Contrôle BAT.
// Mocke `global.fetch` (même pattern que MatcherOutilButton.test.tsx).

function buildProduction(
  overrides: Partial<ProductionActive> = {},
): ProductionActive {
  return {
    devis_id: 1,
    devis_numero: "DEV-2026-0001",
    client_nom: "ACME SAS",
    designation: "Étiquette miel 50×80 mm",
    machine_id: 10,
    machine_nom: "Mark Andy P5",
    bat_reference_uploaded: true,
    ...overrides,
  };
}

interface MockResponse {
  urlPart: string;
  method?: string;
  body: unknown;
  status?: number;
}

function installFetchMock(responses: MockResponse[]) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : (input as Request).url;
    const method = init?.method ?? "GET";
    const match = responses.find((r) => {
      if (r.method && r.method !== method) return false;
      return url.includes(r.urlPart);
    });
    if (!match) {
      throw new Error(`No mock for ${method} ${url}`);
    }
    const status = match.status ?? 200;
    return {
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? "OK" : "Error",
      json: async () => match.body,
    } as Response;
  }) as typeof fetch;
}

describe("listProductionsActives", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renvoie la liste paginée des productions actives", async () => {
    const items = [
      buildProduction({ devis_id: 1, devis_numero: "DEV-2026-0001" }),
      buildProduction({
        devis_id: 2,
        devis_numero: "DEV-2026-0002",
        client_nom: null,
        designation: null,
        bat_reference_uploaded: false,
      }),
    ];
    installFetchMock([
      {
        urlPart: "/api/flexocheck/productions-actives",
        body: { items, total: 2 },
      },
    ]);

    const res = await listProductionsActives();
    expect(res.total).toBe(2);
    expect(res.items).toHaveLength(2);
    expect(res.items[0]!.devis_numero).toBe("DEV-2026-0001");
    expect(res.items[1]!.bat_reference_uploaded).toBe(false);
  });

  it("envoie le bearer token si présent dans localStorage", async () => {
    window.localStorage.setItem("devis_flexo_access_token", "tok-abc");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ items: [], total: 0 }),
    })) as unknown as typeof fetch;
    global.fetch = fetchMock;

    await listProductionsActives();

    const callArgs = (fetchMock as unknown as { mock: { calls: unknown[][] } })
      .mock.calls[0];
    const init = callArgs?.[1] as RequestInit | undefined;
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok-abc");
  });

  it("403 backend (has_flexocheck=false) → ApiError 403 avec detail", async () => {
    installFetchMock([
      {
        urlPart: "/api/flexocheck/productions-actives",
        status: 403,
        body: { detail: "Module FlexoCheck non activé" },
      },
    ]);

    await expect(listProductionsActives()).rejects.toMatchObject({
      status: 403,
    });
    await expect(listProductionsActives()).rejects.toBeInstanceOf(ApiError);
  });

  it("500 backend sans body JSON → ApiError 500 avec statusText", async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;

    await expect(listProductionsActives()).rejects.toMatchObject({
      status: 500,
    });
  });
});

describe("uploadBatReference", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POST multipart/form-data avec devis_id + file, renvoie la réponse JSON", async () => {
    window.localStorage.setItem("devis_flexo_access_token", "tok-xyz");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        devis_id: 42,
        bat_filename: "bat-acme.pdf",
        bat_mime_type: "application/pdf",
        bat_uploaded_at: "2026-05-24T10:00:00",
      }),
    })) as unknown as typeof fetch;
    global.fetch = fetchMock;

    const file = new File(["PDFDATA"], "bat-acme.pdf", {
      type: "application/pdf",
    });
    const res = await uploadBatReference(42, file);

    expect(res.devis_id).toBe(42);
    expect(res.bat_filename).toBe("bat-acme.pdf");

    const callArgs = (fetchMock as unknown as { mock: { calls: unknown[][] } })
      .mock.calls[0];
    const url = callArgs?.[0] as string;
    const init = callArgs?.[1] as RequestInit | undefined;
    expect(url).toContain("/api/flexocheck/controle-bat/upload-bat");
    expect(init?.method).toBe("POST");
    // Bearer présent, pas de Content-Type manuel (FormData → browser handles).
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok-xyz");
    expect(headers["Content-Type"]).toBeUndefined();
    // Body est bien une FormData avec devis_id + file.
    expect(init?.body).toBeInstanceOf(FormData);
    const fd = init?.body as FormData;
    expect(fd.get("devis_id")).toBe("42");
    expect(fd.get("file")).toBeInstanceOf(File);
    expect((fd.get("file") as File).name).toBe("bat-acme.pdf");
  });

  it("422 backend (devis introuvable) → ApiError 422 avec detail", async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: async () => ({ detail: "Devis 999 introuvable" }),
    })) as unknown as typeof fetch;

    const file = new File(["x"], "bat.pdf", { type: "application/pdf" });
    await expect(uploadBatReference(999, file)).rejects.toMatchObject({
      status: 422,
    });
    await expect(uploadBatReference(999, file)).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});
