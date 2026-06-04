import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useEffect } from "react";

import type { OptimisationConfigOut } from "@/lib/api";

import { OptimisationPoseCandidats } from "./OptimisationPoseCandidats";
import {
  buildIdCandidat,
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
function Seeder({
  candidats,
  nbFronts,
}: {
  candidats: OptimisationConfigOut[];
  nbFronts?: number;
}) {
  const { goCandidats, setBriefClient } = useOptimisationPose();
  useEffect(() => {
    if (nbFronts !== undefined) {
      setBriefClient({ nb_fronts_sortie: nbFronts });
    }
    goCandidats(candidats, 10_000, 100, 80, 76);
  }, [goCandidats, setBriefClient, candidats, nbFronts]);
  return null;
}

function renderAvecCandidats(
  candidats: OptimisationConfigOut[],
  nbFronts?: number,
) {
  return render(
    <OptimisationPoseProvider>
      <Seeder candidats={candidats} nbFronts={nbFronts} />
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

// Règle métier (Eric) — nb_poses_laize doit être un MULTIPLE de
// nb_fronts_sortie. Cohérent ⟺ nb_poses_laize % nb_fronts === 0.
describe("OptimisationPoseCandidats — cohérence fronts ↔ poses laize", () => {
  it("nb_fronts=1 (défaut) : neutre — aucun badge, rien bloqué, pas de toggle", () => {
    const c = makeCandidat({ nb_poses_laize: 3 });
    renderAvecCandidats([c]); // nbFronts non fourni → défaut 1
    const id = buildIdCandidat(c);

    expect(
      screen.queryByTestId(`badge-incoherent-${id}`),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId(`candidat-checkbox-${id}`)).not.toBeDisabled();
    // Le toggle n'apparaît que si la règle s'applique (nbFronts > 1).
    expect(
      screen.queryByTestId("toggle-masquer-incoherents"),
    ).not.toBeInTheDocument();
  });

  it("nb_fronts=2 : laize impaire = incohérente (badge + bloquée), laize paire = OK", () => {
    const impair = makeCandidat({ nb_poses_laize: 3 });
    const pair = makeCandidat({ nb_poses_laize: 4 });
    renderAvecCandidats([impair, pair], 2);
    const idImpair = buildIdCandidat(impair);
    const idPair = buildIdCandidat(pair);

    expect(
      screen.getByTestId(`badge-incoherent-${idImpair}`),
    ).toHaveTextContent("incompatible avec 2 fronts");
    expect(screen.getByTestId(`candidat-checkbox-${idImpair}`)).toBeDisabled();

    expect(
      screen.queryByTestId(`badge-incoherent-${idPair}`),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId(`candidat-checkbox-${idPair}`)).not.toBeDisabled();
  });

  it("toggle « Masquer les incohérents » : filtre les incohérents, garde les cohérents", async () => {
    const impair = makeCandidat({ nb_poses_laize: 3 });
    const pair = makeCandidat({ nb_poses_laize: 4 });
    renderAvecCandidats([impair, pair], 2);
    const idImpair = buildIdCandidat(impair);
    const idPair = buildIdCandidat(pair);

    // Défaut OFF → les deux lignes visibles.
    expect(screen.getByTestId(`candidat-row-${idImpair}`)).toBeInTheDocument();
    expect(screen.getByTestId(`candidat-row-${idPair}`)).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("toggle-masquer-incoherents"));

    expect(
      screen.queryByTestId(`candidat-row-${idImpair}`),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId(`candidat-row-${idPair}`)).toBeInTheDocument();
  });

  it("nb_fronts=3 : seuls les multiples de 3 sont sélectionnables", () => {
    const c3 = makeCandidat({ nb_poses_laize: 3 });
    const c4 = makeCandidat({ nb_poses_laize: 4 });
    const c6 = makeCandidat({ nb_poses_laize: 6 });
    renderAvecCandidats([c3, c4, c6], 3);

    expect(
      screen.getByTestId(`candidat-checkbox-${buildIdCandidat(c3)}`),
    ).not.toBeDisabled();
    expect(
      screen.getByTestId(`candidat-checkbox-${buildIdCandidat(c4)}`),
    ).toBeDisabled();
    expect(
      screen.getByTestId(`candidat-checkbox-${buildIdCandidat(c6)}`),
    ).not.toBeDisabled();
  });
});
