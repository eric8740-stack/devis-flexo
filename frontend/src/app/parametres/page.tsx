import { redirect } from "next/navigation";

// Sprint 9 v2 : /parametres redirige vers /parametres/tarifs (priorité 1).
// L'EntrepriseForm vit désormais dans /parametres/entreprise.
export default function ParametresIndex() {
  redirect("/parametres/tarifs");
}
