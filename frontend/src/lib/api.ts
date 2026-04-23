const API_URL = "http://localhost:8000";

export interface Entreprise {
  id: number;
  raison_sociale: string;
  siret: string;
  adresse: string | null;
  cp: string | null;
  ville: string | null;
  tel: string | null;
  email: string | null;
  pct_fg: number | null;
  pct_marge_defaut: number | null;
  heures_prod_presse_mois: number | null;
  heures_prod_finition_mois: number | null;
}

export type EntrepriseUpdate = Omit<Entreprise, "id">;

export async function getEntreprise(): Promise<Entreprise> {
  const response = await fetch(`${API_URL}/api/entreprise`);
  if (!response.ok) {
    throw new Error(
      `GET /api/entreprise a échoué : ${response.status} ${response.statusText}`
    );
  }
  return response.json();
}

export async function updateEntreprise(
  data: EntrepriseUpdate
): Promise<Entreprise> {
  const response = await fetch(`${API_URL}/api/entreprise`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(
      `PUT /api/entreprise a échoué : ${response.status} ${response.statusText}`
    );
  }
  return response.json();
}
