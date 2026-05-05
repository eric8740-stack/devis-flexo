// Types frontend correspondant aux schémas Pydantic admin (Sprint 12 Lot S12-D).

export interface AdminUser {
  id: number;
  email: string;
  nom_contact: string;
  is_active: boolean;
  is_admin: boolean;
  entreprise_id: number;
  nom_entreprise: string;
  is_demo: boolean;
  date_creation: string;
  date_derniere_connexion: string | null;
}

export interface AdminUserCreate {
  email: string;
  password: string;
  nom_entreprise: string;
  nom_contact: string;
  is_admin: boolean;
}
