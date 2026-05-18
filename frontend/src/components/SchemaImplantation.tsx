"use client";

import Image from "next/image";

import { type OptimisationConfigOut, type SensEnroulement } from "@/lib/api";

/**
 * Schéma BAT (Bon À Tirer) — version professionnelle.
 *
 * 3 vues complémentaires en SVG inline responsive :
 *   A. Plaque vue de face   — laize papier + plaque centrée + poses
 *   B. Bobine livrée        — vue schématique de profil (façon atelier flexo)
 *                             avec le sens d'enroulement correctement rendu
 *   C. Bobine fille (client) — bande liner + étiquettes alignées
 *
 * Couleurs métier hardcodées inline (cohérent stack Tailwind sans CSS vars
 * custom) : bleu #0C447C, bleu clair #DCE7F3, orange #993C1D (repère START
 * + intervalles), liner #FAF7EE + hachures #C8C6BC, gris #6B7280 (mandrin).
 */

const COULEUR_BLEU = "#0C447C";
const COULEUR_BLEU_CLAIR = "#DCE7F3";
const COULEUR_ORANGE = "#993C1D";
const COULEUR_GRIS_FONCE = "#374151";
const COULEUR_GRIS = "#9CA3AF";
const COULEUR_LINER = "#FAF7EE";
const COULEUR_HACHURE = "#C8C6BC";
// Sens intérieur (SE5-8) : la face imprimée est tournée vers l'intérieur de
// la bobine. Le client voit le liner siliconé translucide PAR-DESSUS
// l'étiquette → teinte jaune-beige caractéristique de l'aspect "vu à travers
// le liner". Sens extérieur (SE1-4) : étiquettes bleu clair franc.
const COULEUR_ETIQ_INT = "#F0E4B4"; // jaune-beige liner translucide
const COULEUR_ETIQ_INT_BORDURE = "#9C8E4E";

interface Props {
  config: OptimisationConfigOut;
  laizeEtiqMm: number;
  devEtiqMm: number;
  mandrinMm: number;
}

export function SchemaImplantation({
  config,
  laizeEtiqMm,
  devEtiqMm,
  mandrinMm,
}: Props) {
  return (
    <div className="rounded-md border border-border bg-muted/30 p-4">
      <div className="grid gap-6 lg:grid-cols-2">
        <VuePlaque
          config={config}
          laizeEtiqMm={laizeEtiqMm}
          devEtiqMm={devEtiqMm}
        />
        <VueBobine
          config={config}
          laizeEtiqMm={laizeEtiqMm}
          devEtiqMm={devEtiqMm}
          mandrinMm={mandrinMm}
        />
      </div>
      <div className="mt-6 border-t border-border pt-4">
        <VueBobineFille
          config={config}
          laizeEtiqMm={laizeEtiqMm}
          devEtiqMm={devEtiqMm}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers — orientation du A selon le sens d'enroulement
// ---------------------------------------------------------------------------

/**
 * Indique si le sens est "intérieur" (faces dedans, étiquettes vues à
 * travers le liner siliconé translucide → teinte jaune-beige).
 *
 * Les ROTATIONS du A sur VUE A et VUE C viennent désormais directement du
 * backend (`config.rotation_vue_a_deg` / `rotation_vue_c_deg`, single
 * source of truth dans `services/rotation_se.py`). Plus de mapping local.
 */
function isFaceInt(se: SensEnroulement): boolean {
  return ["SE5", "SE6", "SE7", "SE8"].includes(se);
}

// ---------------------------------------------------------------------------
// VUE A — plaque (vue de face), compacte et centrée
// ---------------------------------------------------------------------------

function VuePlaque({
  config,
  laizeEtiqMm,
  devEtiqMm,
}: Omit<Props, "mandrinMm">) {
  // viewBox compact : on cale sur 460 unités horizontalement et on dérive la
  // hauteur en fonction du ratio Z / laize_papier. Largeur utile réduite
  // à 280 pour laisser de la marge aux cotes externes.
  const VBW = 460;
  const innerW = 280;
  const ratio = config.z_cylindre_mm / config.laize_papier_mm;
  const innerH = Math.min(Math.max(innerW * ratio, 160), 460);
  const VBH = innerH + 170;

  // Centrage horizontal strict
  const ox = (VBW - innerW) / 2;
  const oy = 80;

  const widthPapier = innerW;
  const widthPlaque =
    (config.laize_plaque_mm / config.laize_papier_mm) * innerW;
  const chuteW = (widthPapier - widthPlaque) / 2;

  const poseW = widthPlaque / config.nb_poses_laize;
  const poseH = innerH / config.nb_poses_dev;
  const intervalleLaizeUnits =
    (config.intervalle_laize_reel_mm / config.laize_papier_mm) * innerW;
  const intervalleDevUnits =
    (config.intervalle_dev_reel_mm / config.z_cylindre_mm) * innerH;

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue A — plaque (sens machine)
      </figcaption>
      <svg
        viewBox={`0 0 ${VBW} ${VBH}`}
        width="100%"
        className="font-sans"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <pattern
            id="hachures-chute"
            patternUnits="userSpaceOnUse"
            width={6}
            height={6}
            patternTransform="rotate(45)"
          >
            <line
              x1={0}
              y1={0}
              x2={0}
              y2={6}
              stroke={COULEUR_HACHURE}
              strokeWidth={0.8}
            />
          </pattern>
          <marker
            id="arrow-bleu-a"
            viewBox="0 0 10 10"
            refX={5}
            refY={5}
            markerWidth={6}
            markerHeight={6}
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={COULEUR_BLEU} />
          </marker>
        </defs>

        {/* Bloc identité cylindre (en haut, voyant) */}
        <g transform={`translate(${VBW / 2}, 26)`}>
          <rect
            x={-115}
            y={-20}
            width={230}
            height={40}
            rx={6}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.8}
          />
          <text
            x={0}
            y={-3}
            textAnchor="middle"
            fontSize={13}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            Cylindre {config.nb_dents_cylindre} dents
          </text>
          <text
            x={0}
            y={13}
            textAnchor="middle"
            fontSize={10}
            fill={COULEUR_BLEU}
          >
            Développé Z = {config.z_cylindre_mm} mm
          </text>
        </g>

        {/* Cadre laize papier (pointillé) */}
        <rect
          x={ox}
          y={oy}
          width={widthPapier}
          height={innerH}
          fill="none"
          stroke={COULEUR_HACHURE}
          strokeWidth={0.5}
          strokeDasharray="3 2"
        />

        {/* Chutes latérales hachurées */}
        <rect
          x={ox}
          y={oy}
          width={chuteW}
          height={innerH}
          fill="url(#hachures-chute)"
          opacity={0.6}
        />
        <rect
          x={ox + widthPapier - chuteW}
          y={oy}
          width={chuteW}
          height={innerH}
          fill="url(#hachures-chute)"
          opacity={0.6}
        />

        {/* Plaque imprimée centrée dans la laize papier */}
        <rect
          x={ox + chuteW}
          y={oy}
          width={widthPlaque}
          height={innerH}
          fill="none"
          stroke={COULEUR_BLEU}
          strokeWidth={1}
        />

        {/* Grille des poses.
            La rotation du A suit le sens d'enroulement choisi (SE1=0°, SE2=180°,
            SE3=270°, SE4=90°), ce qui aligne la VUE A (plaque) sur la VUE C
            (bobine fille déroulée chez le client) — le A vu en sortie de
            presse = le A vu par le client final. */}
        {Array.from({ length: config.nb_poses_dev }).map((_, row) =>
          Array.from({ length: config.nb_poses_laize }).map((__, col) => {
            const px = ox + chuteW + col * poseW;
            const py = oy + row * poseH;
            const cxA = px + poseW / 2;
            const cyA = py + poseH / 2;
            const aRotation = config.rotation_vue_a_deg;
            return (
              <g key={`pose-${row}-${col}`}>
                <rect
                  x={px + 1.5}
                  y={py + 1.5}
                  width={poseW - 3}
                  height={poseH - 3}
                  fill={COULEUR_BLEU_CLAIR}
                  stroke={COULEUR_BLEU}
                  strokeWidth={0.4}
                />
                <g transform={`translate(${cxA} ${cyA}) rotate(${aRotation})`}>
                  <text
                    x={0}
                    y={0}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={Math.min(poseW, poseH) * 0.42}
                    fontWeight={700}
                    fill={COULEUR_BLEU}
                  >
                    A
                  </text>
                </g>
              </g>
            );
          })
        )}

        {/* Cote laize papier (haut, gras) */}
        <line
          x1={ox}
          y1={oy - 20}
          x2={ox + widthPapier}
          y2={oy - 20}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line x1={ox} y1={oy - 24} x2={ox} y2={oy} stroke={COULEUR_BLEU} strokeWidth={0.4} />
        <line
          x1={ox + widthPapier}
          y1={oy - 24}
          x2={ox + widthPapier}
          y2={oy}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={ox + widthPapier / 2}
          y={oy - 24}
          textAnchor="middle"
          fontSize={11}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          LAIZE {config.laize_papier_mm} mm
        </text>

        {/* Cote laize plaque (bas, gris) */}
        <line
          x1={ox + chuteW}
          y1={oy + innerH + 15}
          x2={ox + chuteW + widthPlaque}
          y2={oy + innerH + 15}
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.6}
        />
        <text
          x={ox + chuteW + widthPlaque / 2}
          y={oy + innerH + 27}
          textAnchor="middle"
          fontSize={10}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
        >
          Laize plaque {config.laize_plaque_mm} mm
        </text>

        {/* Cotes zones d'enchenillage (chutes latérales gauche/droite) */}
        <text
          x={ox + chuteW / 2}
          y={oy + innerH + 42}
          textAnchor="middle"
          fontSize={8}
          fill={COULEUR_GRIS}
        >
          Zone enchenillage {config.chute_laterale_reelle_mm}
        </text>
        <text
          x={ox + widthPapier - chuteW / 2}
          y={oy + innerH + 42}
          textAnchor="middle"
          fontSize={8}
          fill={COULEUR_GRIS}
        >
          Zone enchenillage {config.chute_laterale_reelle_mm}
        </text>

        {/* Cote Z cylindre à droite (verticale) */}
        <line
          x1={ox + widthPapier + 24}
          y1={oy}
          x2={ox + widthPapier + 24}
          y2={oy + innerH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line
          x1={ox + widthPapier + 20}
          y1={oy}
          x2={ox + widthPapier + 28}
          y2={oy}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <line
          x1={ox + widthPapier + 20}
          y1={oy + innerH}
          x2={ox + widthPapier + 28}
          y2={oy + innerH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={ox + widthPapier + 32}
          y={oy + innerH / 2 - 6}
          fontSize={10}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          Z {config.z_cylindre_mm}
        </text>
        <text
          x={ox + widthPapier + 32}
          y={oy + innerH / 2 + 6}
          fontSize={9}
          fill={COULEUR_BLEU}
        >
          {config.nb_dents_cylindre} dents
        </text>

        {/* Cotes Écart entre chaque étiquette (sens laize & sens dev) en orange */}
        {config.nb_poses_laize > 1 && (
          <g>
            <line
              x1={ox + chuteW + poseW - intervalleLaizeUnits / 2}
              y1={oy - 6}
              x2={ox + chuteW + poseW + intervalleLaizeUnits / 2}
              y2={oy - 6}
              stroke={COULEUR_ORANGE}
              strokeWidth={0.7}
              strokeDasharray="2 1"
            />
            <text
              x={ox + chuteW + poseW}
              y={oy - 9}
              textAnchor="middle"
              fontSize={9}
              fill={COULEUR_ORANGE}
            >
              écart {config.intervalle_laize_reel_mm}
            </text>
          </g>
        )}
        {config.nb_poses_dev > 1 && (
          <g>
            <line
              x1={ox - 6}
              y1={oy + poseH - intervalleDevUnits / 2}
              x2={ox - 6}
              y2={oy + poseH + intervalleDevUnits / 2}
              stroke={COULEUR_ORANGE}
              strokeWidth={0.7}
              strokeDasharray="2 1"
            />
            <text
              x={ox - 10}
              y={oy + poseH}
              textAnchor="end"
              fontSize={9}
              fill={COULEUR_ORANGE}
              dominantBaseline="middle"
            >
              écart {config.intervalle_dev_reel_mm}
            </text>
          </g>
        )}

        {/* Flèche défilement à gauche : badge bleu pâle bordé + grosse flèche
            verticale épaisse, label rotaté à côté. Doit se voir au premier
            coup d'œil (retour Eric). */}
        <g transform={`translate(${ox - 40}, ${oy + innerH / 2})`}>
          <rect
            x={-18}
            y={-50}
            width={26}
            height={100}
            rx={4}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.6}
          />
          <line
            x1={-5}
            y1={-38}
            x2={-5}
            y2={38}
            stroke={COULEUR_BLEU}
            strokeWidth={2.5}
            markerEnd="url(#arrow-bleu-a)"
          />
          <text
            x={9}
            y={0}
            fontSize={10}
            fontWeight={700}
            fill={COULEUR_BLEU}
            textAnchor="middle"
            transform={`rotate(-90 9 0)`}
          >
            AVANCE
          </text>
        </g>

        {/* Cote "Pas en Avance" = dev étiquette + écart entre étiquettes.
            C'est la longueur consommée sur le cylindre par une rangée. */}
        {config.nb_poses_dev > 1 && (
          <text
            x={VBW / 2}
            y={VBH - 28}
            textAnchor="middle"
            fontSize={10}
            fontWeight={600}
            fill={COULEUR_ORANGE}
          >
            Pas en Avance = {devEtiqMm} + {config.intervalle_dev_reel_mm} ={" "}
            {(devEtiqMm + config.intervalle_dev_reel_mm).toFixed(2)} mm
          </text>
        )}

        {/* Légende dimensions */}
        <text
          x={VBW / 2}
          y={VBH - 10}
          textAnchor="middle"
          fontSize={10}
          fill={COULEUR_GRIS_FONCE}
          fontStyle="italic"
        >
          Étiquette LAIZE {laizeEtiqMm} × dev {devEtiqMm} mm — {config.nb_poses_laize}{" "}
          × {config.nb_poses_dev} = {config.nb_poses_total} poses
        </text>
      </svg>
    </figure>
  );
}

// ---------------------------------------------------------------------------
// VUE B — bobine livrée (vue schématique simple, façon atelier flexo)
// ---------------------------------------------------------------------------


function VueBobine({
  config,
  laizeEtiqMm,
  devEtiqMm,
  mandrinMm,
}: {
  config: OptimisationConfigOut;
  laizeEtiqMm: number;
  devEtiqMm: number;
  mandrinMm: number;
}) {
  // VUE B utilise les illustrations Canva (style atelier flexo). L'image
  // change selon le sens d'enroulement choisi et porte des annotations
  // a/b/c/d/e/f/X/Y dont les valeurs correspondent au tableau ci-dessous
  // (cartouche cotes affiché sous l'image, layout cohérent avec la VUE A à
  // gauche).
  const idx = parseInt(config.sens_enroulement.replace("SE", ""), 10);

  // Cadre X/Y unitaire : copie de l'étiquette telle qu'elle apparaît en
  // VUE C (vue client en décollant). Convention verrouillée :
  //   X = dev (horizontal), Y = laize (vertical),
  //   A pivoté selon rotation_vue_c_deg (single source of truth backend).
  const CADRE_MAX_PX = 80;
  const cadreScale = CADRE_MAX_PX / Math.max(devEtiqMm, laizeEtiqMm);
  const cadreW = devEtiqMm * cadreScale;
  const cadreH = laizeEtiqMm * cadreScale;
  const cadreCx = 70;
  const cadreCy = 75;
  const cadreOx = cadreCx - cadreW / 2;
  const cadreOy = cadreCy - cadreH / 2;
  const cadreFaceInt = isFaceInt(config.sens_enroulement);
  const cadreFill = cadreFaceInt ? COULEUR_ETIQ_INT : COULEUR_BLEU_CLAIR;
  const cadreStroke = cadreFaceInt ? COULEUR_ETIQ_INT_BORDURE : COULEUR_BLEU;
  const cadreAFill = cadreFaceInt ? COULEUR_GRIS_FONCE : COULEUR_BLEU;
  const cadreAFont = Math.min(cadreW, cadreH) * 0.55;

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue B — bobine livrée
      </figcaption>
      <div className="overflow-hidden rounded border border-border bg-white">
        <Image
          src={`/assets/bobines/sens-${idx}.png`}
          alt={`Bobine ${config.sens_enroulement} — ${config.sens_enroulement_libelle}`}
          width={1200}
          height={1200}
          className="h-auto w-full"
          sizes="(min-width: 1024px) 50vw, 100vw"
          priority={false}
        />
      </div>

      {/* Badge SE — libellé officiel depuis backend */}
      <div className="rounded border border-blue-300 bg-blue-50/50 px-2 py-1">
        <div className="text-xs font-semibold text-blue-900">
          {config.sens_enroulement_libelle}
        </div>
      </div>

      {/* Cadre X/Y unitaire — copie de l'étiquette telle que vue en VUE C
          (dev horizontal × laize vertical, A pivoté selon backend). */}
      <div className="rounded border border-border bg-white p-2">
        <p className="mb-1 text-center text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Cadre étiquette unitaire (= vue client)
        </p>
        <svg
          viewBox="0 0 140 140"
          width="100%"
          className="mx-auto max-w-[180px]"
          preserveAspectRatio="xMidYMid meet"
        >
          <rect
            x={cadreOx}
            y={cadreOy}
            width={cadreW}
            height={cadreH}
            fill={cadreFill}
            stroke={cadreStroke}
            strokeWidth={1}
          />
          <g
            transform={`translate(${cadreCx} ${cadreCy}) rotate(${config.rotation_vue_c_deg})`}
          >
            <text
              x={0}
              y={0}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={cadreAFont}
              fontWeight={700}
              fill={cadreAFill}
            >
              A
            </text>
          </g>

          {/* X = dev — cote horizontale au-dessus du cadre */}
          <line
            x1={cadreOx}
            y1={cadreOy - 8}
            x2={cadreOx + cadreW}
            y2={cadreOy - 8}
            stroke={COULEUR_BLEU}
            strokeWidth={0.7}
          />
          <line
            x1={cadreOx}
            y1={cadreOy - 11}
            x2={cadreOx}
            y2={cadreOy - 5}
            stroke={COULEUR_BLEU}
            strokeWidth={0.5}
          />
          <line
            x1={cadreOx + cadreW}
            y1={cadreOy - 11}
            x2={cadreOx + cadreW}
            y2={cadreOy - 5}
            stroke={COULEUR_BLEU}
            strokeWidth={0.5}
          />
          <text
            x={cadreCx}
            y={cadreOy - 12}
            textAnchor="middle"
            fontSize={7}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            X = dev {devEtiqMm} mm
          </text>

          {/* Y = laize — cote verticale à droite du cadre */}
          <line
            x1={cadreOx + cadreW + 8}
            y1={cadreOy}
            x2={cadreOx + cadreW + 8}
            y2={cadreOy + cadreH}
            stroke={COULEUR_BLEU}
            strokeWidth={0.7}
          />
          <line
            x1={cadreOx + cadreW + 5}
            y1={cadreOy}
            x2={cadreOx + cadreW + 11}
            y2={cadreOy}
            stroke={COULEUR_BLEU}
            strokeWidth={0.5}
          />
          <line
            x1={cadreOx + cadreW + 5}
            y1={cadreOy + cadreH}
            x2={cadreOx + cadreW + 11}
            y2={cadreOy + cadreH}
            stroke={COULEUR_BLEU}
            strokeWidth={0.5}
          />
          <text
            x={cadreOx + cadreW + 13}
            y={cadreCy - 4}
            textAnchor="start"
            dominantBaseline="central"
            fontSize={7}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            Y = laize
          </text>
          <text
            x={cadreOx + cadreW + 13}
            y={cadreCy + 4}
            textAnchor="start"
            dominantBaseline="central"
            fontSize={7}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            {laizeEtiqMm} mm
          </text>
        </svg>
      </div>

      {/* Cartouche cotes a/b/c/d/e/f + X/Y. X = dev (horizontal), Y = laize
          (vertical) — convention VUE C verrouillée 18/05/2026. */}
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 rounded border border-border bg-white p-2 text-xs sm:grid-cols-3">
        <Cote
          letter="a"
          label="écart entre étiquettes"
          value={`${config.intervalle_dev_reel_mm} mm`}
        />
        <Cote
          letter="b"
          label="lacet droit"
          value={`${config.lacet_droit_mm} mm`}
        />
        <Cote
          letter="c"
          label="lacet gauche"
          value={`${config.lacet_gauche_mm} mm`}
        />
        <Cote
          letter="d"
          label="laize bobine totale"
          value={`${config.laize_papier_mm} mm`}
        />
        <Cote
          letter="e"
          label="Ø Diamètre Total Bobine"
          value={`${config.diametre_bobine_mm} mm`}
          strong
        />
        <Cote
          letter="f"
          label="Ø Mandrin"
          value={`${mandrinMm} mm`}
        />
        <Cote letter="X" label="dev étiquette" value={`${devEtiqMm} mm`} />
        <Cote letter="Y" label="laize étiquette" value={`${laizeEtiqMm} mm`} />
        <Cote
          label="Mètres linéaires totaux"
          value={`${config.ml_total_m} m`}
        />
      </dl>
    </figure>
  );
}

function Cote({
  letter,
  label,
  value,
  strong = false,
}: {
  letter?: string;
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-1.5 py-0.5">
      <dt className="flex items-baseline gap-1 text-muted-foreground">
        {letter && (
          <span className="inline-flex h-4 min-w-[1rem] items-center justify-center rounded bg-blue-100 px-1 text-[10px] font-bold text-blue-900">
            {letter}
          </span>
        )}
        <span>{label}</span>
      </dt>
      <dd className={strong ? "font-semibold" : "font-medium"}>{value}</dd>
    </div>
  );
}

// ---------------------------------------------------------------------------
// VUE C — bobine fille déroulée (chez le client)
// ---------------------------------------------------------------------------

function VueBobineFille({
  config,
  laizeEtiqMm,
  devEtiqMm,
}: {
  config: OptimisationConfigOut;
  laizeEtiqMm: number;
  devEtiqMm: number;
}) {
  const faceInt = isFaceInt(config.sens_enroulement);
  const VBW = 720;
  const VBH = 260;
  const NB_ETIQ_AFFICHEES = 5;
  const ox = 60;
  const oy = 60;
  const innerW = VBW - 120;

  const intervalleDevUnits = (innerW / NB_ETIQ_AFFICHEES) * 0.08;
  const etiqW =
    (innerW - intervalleDevUnits * (NB_ETIQ_AFFICHEES - 1)) /
    NB_ETIQ_AFFICHEES;
  const aspectEtiq = laizeEtiqMm / devEtiqMm;
  const etiqH = etiqW * aspectEtiq;
  const linerH = etiqH + 20;

  // Sens intérieur (SE5-8) : étiquettes vues à travers le liner siliconé
  // (face dedans) → teinte jaune-beige. Sens extérieur : bleu clair.
  const etiqFill = faceInt ? COULEUR_ETIQ_INT : COULEUR_BLEU_CLAIR;
  const etiqStroke = faceInt ? COULEUR_ETIQ_INT_BORDURE : COULEUR_BLEU;
  const aFill = faceInt ? COULEUR_GRIS_FONCE : COULEUR_BLEU;

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue C — bobine fille déroulée chez le client
      </figcaption>
      <p className="text-xs text-muted-foreground">
        Laize liner {config.laize_liner_mm} mm · Sens{" "}
        {config.sens_enroulement.replace("SE", "")} —{" "}
        {config.sens_enroulement_libelle} · ml total {config.ml_total_m} m
      </p>
      <svg
        viewBox={`0 0 ${VBW} ${VBH}`}
        width="100%"
        className="font-sans"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <pattern
            id="liner-dots-c"
            patternUnits="userSpaceOnUse"
            width={8}
            height={8}
          >
            <circle cx={2} cy={2} r={0.6} fill={COULEUR_HACHURE} />
          </pattern>
          <marker
            id="arrow-bleu-c"
            viewBox="0 0 10 10"
            refX={9}
            refY={5}
            markerWidth={9}
            markerHeight={9}
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={COULEUR_BLEU} />
          </marker>
        </defs>

        <rect
          x={ox}
          y={oy - 10}
          width={innerW}
          height={linerH}
          fill={COULEUR_LINER}
          stroke={COULEUR_HACHURE}
          strokeWidth={0.6}
        />
        <rect
          x={ox}
          y={oy - 10}
          width={innerW}
          height={linerH}
          fill="url(#liner-dots-c)"
          opacity={0.5}
        />

        {/* VUE C — rotation A selon mapping officiel verrouillé 18/05/2026
            (cf services/rotation_se.py). Référentiel client : défilement
            horizontal vers la droite. Paires ext/int partagent même
            rotation (la face dehors/dedans est portée par VUE B). */}
        {Array.from({ length: NB_ETIQ_AFFICHEES }).map((_, i) => {
          const px = ox + i * (etiqW + intervalleDevUnits);
          const cxA = px + etiqW / 2;
          const cyA = oy + etiqH / 2;
          const aRotation = config.rotation_vue_c_deg;
          return (
            <g key={i}>
              <rect
                x={px}
                y={oy}
                width={etiqW}
                height={etiqH}
                fill={etiqFill}
                stroke={etiqStroke}
                strokeWidth={0.8}
              />
              <g transform={`translate(${cxA} ${cyA}) rotate(${aRotation})`}>
                <text
                  x={0}
                  y={0}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={etiqH * 0.5}
                  fontWeight={700}
                  fill={aFill}
                >
                  A
                </text>
              </g>
            </g>
          );
        })}

        <line
          x1={ox}
          y1={oy - 22}
          x2={ox + etiqW}
          y2={oy - 22}
          stroke={COULEUR_BLEU}
          strokeWidth={0.7}
        />
        <line x1={ox} y1={oy - 27} x2={ox} y2={oy - 17} stroke={COULEUR_BLEU} strokeWidth={0.4} />
        <line
          x1={ox + etiqW}
          y1={oy - 27}
          x2={ox + etiqW}
          y2={oy - 17}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={ox + etiqW / 2}
          y={oy - 28}
          textAnchor="middle"
          fontSize={10}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          dev {devEtiqMm} mm
        </text>

        <text
          x={ox + etiqW + intervalleDevUnits / 2}
          y={oy + etiqH + 24}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_ORANGE}
        >
          écart {config.intervalle_dev_reel_mm}
        </text>

        <line
          x1={VBW - 38}
          y1={oy}
          x2={VBW - 38}
          y2={oy + etiqH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.7}
        />
        <text
          x={VBW - 30}
          y={oy + etiqH / 2}
          fontSize={10}
          fontWeight={700}
          fill={COULEUR_BLEU}
          dominantBaseline="middle"
        >
          laize {laizeEtiqMm}
        </text>

        <line
          x1={28}
          y1={oy - 10}
          x2={28}
          y2={oy - 10 + linerH}
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.7}
        />
        <text
          x={18}
          y={oy - 10 + linerH / 2}
          fontSize={10}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
          textAnchor="end"
          dominantBaseline="middle"
          transform={`rotate(-90 18 ${oy - 10 + linerH / 2})`}
        >
          liner {config.laize_liner_mm}
        </text>

        <g transform={`translate(${VBW / 2}, ${VBH - 30})`}>
          <rect
            x={-150}
            y={-13}
            width={300}
            height={26}
            rx={4}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.6}
          />
          <line
            x1={-110}
            y1={0}
            x2={110}
            y2={0}
            stroke={COULEUR_BLEU}
            strokeWidth={1.5}
            markerEnd="url(#arrow-bleu-c)"
          />
          <text
            x={0}
            y={-3}
            textAnchor="middle"
            fontSize={9}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            Sens de défilement chez le client
          </text>
          <text
            x={0}
            y={8}
            textAnchor="middle"
            fontSize={8}
            fill={COULEUR_BLEU}
          >
            (machine de pose)
          </text>
        </g>
      </svg>

      <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <span
            className="inline-block h-3 w-3 border"
            style={{
              backgroundColor: COULEUR_BLEU_CLAIR,
              borderColor: COULEUR_BLEU,
            }}
          />
          Étiquette adhésive
        </div>
        <div className="flex items-center gap-1">
          <span
            className="inline-block h-3 w-3 border"
            style={{
              backgroundColor: COULEUR_LINER,
              borderColor: COULEUR_HACHURE,
            }}
          />
          Liner siliconé
        </div>
        <div className="flex items-center gap-1 justify-end">
          <span
            className="inline-block h-3 w-3"
            style={{ backgroundColor: COULEUR_ORANGE }}
          />
          Repère START bobine
        </div>
      </div>
    </figure>
  );
}
