import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";

import {
  createControleBat,
  decideControleBat,
  getControleBatContext,
  listProductionsActives,
  relancerTirage,
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

describe("getControleBatContext", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("GET avec bearer, renvoie le contexte (devis, BAT URL/mime)", async () => {
    window.localStorage.setItem("devis_flexo_access_token", "tok-1");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        devis_id: 7,
        devis_numero: "DEV-2026-0007",
        client_nom: "ACME",
        designation: "Étiquette 50×80",
        machine_nom: "Mark Andy P5",
        bat_url: "https://s3.example/bat-7.pdf?sig=abc",
        bat_mime_type: "application/pdf",
      }),
    })) as unknown as typeof fetch;
    global.fetch = fetchMock;

    const ctx = await getControleBatContext(7);
    expect(ctx.devis_id).toBe(7);
    expect(ctx.bat_mime_type).toBe("application/pdf");
    expect(ctx.bat_url).toContain("bat-7.pdf");

    const callArgs = (fetchMock as unknown as { mock: { calls: unknown[][] } })
      .mock.calls[0];
    const url = callArgs?.[0] as string;
    const init = callArgs?.[1] as RequestInit | undefined;
    expect(url).toContain("/api/flexocheck/controle-bat/contexte/7");
    expect(init?.method).toBe("GET");
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok-1");
  });

  it("404 backend (devis inexistant) → ApiError 404 avec detail", async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Devis 999 introuvable" }),
    })) as unknown as typeof fetch;

    await expect(getControleBatContext(999)).rejects.toMatchObject({
      status: 404,
    });
    await expect(getControleBatContext(999)).rejects.toBeInstanceOf(ApiError);
  });
});

describe("createControleBat", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POST multipart avec devis_id + photo, renvoie le résultat IA", async () => {
    window.localStorage.setItem("devis_flexo_access_token", "tok-IA");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        controle_id: 101,
        devis_id: 7,
        tentative: 1,
        score_conformite: 87.5,
        decision_recommandee: "valider",
      }),
    })) as unknown as typeof fetch;
    global.fetch = fetchMock;

    const photo = new File(["JPEGDATA"], "tirage.jpg", {
      type: "image/jpeg",
    });
    const res = await createControleBat(7, photo);
    expect(res.controle_id).toBe(101);
    expect(res.tentative).toBe(1);
    expect(res.decision_recommandee).toBe("valider");

    const callArgs = (fetchMock as unknown as { mock: { calls: unknown[][] } })
      .mock.calls[0];
    const url = callArgs?.[0] as string;
    const init = callArgs?.[1] as RequestInit | undefined;
    expect(url).toContain("/api/flexocheck/controle-bat/");
    expect(init?.method).toBe("POST");
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok-IA");
    expect(headers["Content-Type"]).toBeUndefined();
    expect(init?.body).toBeInstanceOf(FormData);
    const fd = init?.body as FormData;
    expect(fd.get("devis_id")).toBe("7");
    expect((fd.get("photo") as File).name).toBe("tirage.jpg");
  });

  it("503 (service IA indisponible) → ApiError 503", async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 503,
      statusText: "Service Unavailable",
      json: async () => ({ detail: "Service IA temporairement indisponible" }),
    })) as unknown as typeof fetch;

    const photo = new File(["x"], "p.jpg", { type: "image/jpeg" });
    await expect(createControleBat(7, photo)).rejects.toMatchObject({
      status: 503,
    });
  });
});

describe("decideControleBat", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POST JSON avec decision_finale + decideur + motif, renvoie la décision", async () => {
    window.localStorage.setItem("devis_flexo_access_token", "tok-dec");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        controle_id: 101,
        devis_id: 7,
        decision_finale: "valider",
        decideur: "J. Martin",
        motif: "Écart mineur accepté",
        decided_at: "2026-05-24T11:00:00",
      }),
    })) as unknown as typeof fetch;
    global.fetch = fetchMock;

    const res = await decideControleBat(101, {
      decision_finale: "valider",
      decideur: "J. Martin",
      motif: "Écart mineur accepté",
    });
    expect(res.decision_finale).toBe("valider");
    expect(res.decideur).toBe("J. Martin");

    const callArgs = (fetchMock as unknown as { mock: { calls: unknown[][] } })
      .mock.calls[0];
    const url = callArgs?.[0] as string;
    const init = callArgs?.[1] as RequestInit | undefined;
    expect(url).toContain("/api/flexocheck/controle-bat/101/decision");
    expect(init?.method).toBe("POST");
    const headers = init?.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
    expect(headers.Authorization).toBe("Bearer tok-dec");
    const body = JSON.parse(init?.body as string);
    expect(body).toEqual({
      decision_finale: "valider",
      decideur: "J. Martin",
      motif: "Écart mineur accepté",
    });
  });

  it("motif omis : payload sans motif (champ optionnel)", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        controle_id: 102,
        devis_id: 8,
        decision_finale: "valider",
        decideur: "P. Dupond",
        motif: null,
        decided_at: "2026-05-24T11:30:00",
      }),
    })) as unknown as typeof fetch;
    global.fetch = fetchMock;

    await decideControleBat(102, {
      decision_finale: "valider",
      decideur: "P. Dupond",
    });
    const init = (fetchMock as unknown as { mock: { calls: unknown[][] } })
      .mock.calls[0]?.[1] as RequestInit;
    const body = JSON.parse(init.body as string);
    expect(body.motif).toBeUndefined();
  });

  it("409 (décision déjà enregistrée) → ApiError 409", async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 409,
      statusText: "Conflict",
      json: async () => ({ detail: "Décision déjà enregistrée" }),
    })) as unknown as typeof fetch;

    await expect(
      decideControleBat(101, {
        decision_finale: "valider",
        decideur: "J. Martin",
      }),
    ).rejects.toMatchObject({ status: 409 });
  });
});

describe("relancerTirage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POST multipart sur /{id}/retirage avec photo, renvoie ControleBatResult tentative+1", async () => {
    window.localStorage.setItem("devis_flexo_access_token", "tok-rt");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        controle_id: 101,
        devis_id: 7,
        tentative: 2,
        score_conformite: 91.0,
        decision_recommandee: "valider",
      }),
    })) as unknown as typeof fetch;
    global.fetch = fetchMock;

    const photo = new File(["JPEG"], "tirage2.jpg", { type: "image/jpeg" });
    const res = await relancerTirage(101, photo);
    expect(res.tentative).toBe(2);

    const callArgs = (fetchMock as unknown as { mock: { calls: unknown[][] } })
      .mock.calls[0];
    const url = callArgs?.[0] as string;
    const init = callArgs?.[1] as RequestInit | undefined;
    expect(url).toContain("/api/flexocheck/controle-bat/101/retirage");
    expect(init?.method).toBe("POST");
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok-rt");
    expect(headers["Content-Type"]).toBeUndefined();
    expect(init?.body).toBeInstanceOf(FormData);
    const fd = init?.body as FormData;
    expect((fd.get("photo") as File).name).toBe("tirage2.jpg");
    // Le devis_id n'est PAS dans la requête : le backend le résout via
    // /controle-bat/{id}/retirage.
    expect(fd.get("devis_id")).toBeNull();
  });

  it("409 (contrôle déjà décidé) → ApiError 409", async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 409,
      statusText: "Conflict",
      json: async () => ({ detail: "Contrôle déjà clôturé" }),
    })) as unknown as typeof fetch;

    const photo = new File(["x"], "p.jpg", { type: "image/jpeg" });
    await expect(relancerTirage(101, photo)).rejects.toMatchObject({
      status: 409,
    });
  });
});
