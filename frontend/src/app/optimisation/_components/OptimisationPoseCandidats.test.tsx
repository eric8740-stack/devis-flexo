import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useEffect } from "react";

import type { OptimisationConfigOut } from "@/lib/api";

import { OptimisationPoseCandidats } from "./OptimisationPoseCandidats";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./OptimisationPoseStore";

// Bug "3 machines non-candidates" — option (b). Le dédoublonnage moteur
// (_dedoublonner_configs) fusionne les presses de même clé (cylindre/poses/
// intervalles) en une ligne représentante + des équivalentes dans
// `noms_machines_compatibles[1:]`. Ce test verrouille l'affichage VISIBLE
// des équivalentes (et leur masquage quand il n'y en a pas).

/** Construit un candidat minimal viable pour le tableau étape 2. */
function makeCandidat(
  overrides: Partial<OptimisationConfigOut> = {},
): OptimisationConfigOut {
  return {
    cylindre_id: 1,
    machine_id: 1,
    nb_poses_dev: 4,
    nb_poses_laize: 3,
    nb_poses_total: 12,
    intervalle_dev_reel_mm: 2,
    intervalle_laize_reel_mm: 3,
    largeur_plaque_mm: 300,
    z_mini_effet_banane: 0,
    qualite_echenillage: "bonne",
    consolidation_atteinte: false,
    intervalle_laize_souhaitable_mm: null,
    disposition_poses: "alignee",
    coef_vitesse_echenillage: 1,
    coef_gache_echenillage: 1,
    coef_confort_rayon: 1,
    coef_quinconce: 1,
    coef_consolidation: 1,
    coef_vitesse_options: 1,
    coef_gache_options: 1,
    coef_vitesse_final: 1,
    coef_gache_final: 1,
    // Au-dessus du seuil par défaut (30) pour ne pas être filtré.
    score: 90,
    laize_plaque_mm: 300,
    laize_papier_mm: 330,
    chute_laterale_reelle_mm: 3,
    z_cylindre_mm: 330,
    nb_dents_cylindre: 104,
    ml_total_m: 100,
    m2_consomme: 30,
    rendement_pct: 90,
    diametre_bobine_mm: 300,
    laize_liner_mm: 330,
    sens_enroulement: "SE3",
    sens_enroulement_libelle: "0° Extérieur droite avant",
    rotation_vue_a_deg: 0,
    rotation_vue_c_deg: 0,
    machines_compatibles: [1],
    noms_machines_compatibles: ["Mark Andy P5"],
    petit_cylindre: false,
    ...overrides,
  } as OptimisationConfigOut;
}

/** Seede le store avec les candidats fournis puis bascule à l'étape 2. */
function Seeder({ candidats }: { candidats: OptimisationConfigOut[] }) {
  const { goCandidats } = useOptimisationPose();
  useEffect(() => {
    goCandidats(candidats, 10_000, 100, 80, 76);
  }, [goCandidats, candidats]);
  return null;
}

function renderAvecCandidats(candidats: OptimisationConfigOut[]) {
  return render(
    <OptimisationPoseProvider>
      <Seeder candidats={candidats} />
      <OptimisationPoseCandidats />
    </OptimisationPoseProvider>,
  );
}

describe("OptimisationPoseCandidats — machines équivalentes", () => {
  it("affiche les presses équivalentes quand le dédoublonnage en a fusionné", () => {
    const candidat = makeCandidat({
      machines_compatibles: [1, 5, 6],
      noms_machines_compatibles: [
        "Mark Andy P5",
        "OMET XFlex 330",
        "Nilpeter FA-22",
      ],
    });
    renderAvecCandidats([candidat]);

    // La machine représentante reste affichée (présente aussi dans le
    // sélecteur de filtre → getAllByText, au moins une occurrence).
    expect(screen.getAllByText("Mark Andy P5").length).toBeGreaterThan(0);

    // Les équivalentes sont surfacées en texte visible (pas de tooltip).
    const equivalentes = screen.getByTestId("machines-equivalentes");
    expect(equivalentes).toHaveTextContent(
      "Réalisable aussi sur : OMET XFlex 330, Nilpeter FA-22",
    );
  });

  it("n'affiche aucun libellé orphelin quand il n'y a pas d'équivalente", () => {
    const candidat = makeCandidat({
      machines_compatibles: [1],
      noms_machines_compatibles: ["Mark Andy P5"],
    });
    renderAvecCandidats([candidat]);

    expect(screen.getAllByText("Mark Andy P5").length).toBeGreaterThan(0);
    expect(
      screen.queryByTestId("machines-equivalentes"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Réalisable aussi sur/)).not.toBeInTheDocument();
  });
});
