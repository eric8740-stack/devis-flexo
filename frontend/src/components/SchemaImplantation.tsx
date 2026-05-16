"use client";

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
}

export function SchemaImplantation({
  config,
  laizeEtiqMm,
  devEtiqMm,
}: Props) {
  return (
    <div className="rounded-md border border-border bg-muted/30 p-4">
      <div className="grid gap-6 lg:grid-cols-2">
        <VuePlaque
          config={config}
          laizeEtiqMm={laizeEtiqMm}
          devEtiqMm={devEtiqMm}
        />
        <VueBobine config={config} />
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
 * Selon la convention métier flexo 8 sens :
 *   SE1=0° ext   SE2=180° ext   SE3=270° ext   SE4=90° ext
 *   SE5=0° int   SE6=180° int   SE7=270° int   SE8=90° int
 * On dérive la rotation du A et le flag "face intérieur" (bobine inversée).
 */
function parseSE(se: SensEnroulement): {
  rotation: 0 | 90 | 180 | 270;
  faceInt: boolean;
} {
  const map: Record<
    SensEnroulement,
    { rotation: 0 | 90 | 180 | 270; faceInt: boolean }
  > = {
    SE1: { rotation: 0, faceInt: false },
    SE2: { rotation: 180, faceInt: false },
    SE3: { rotation: 270, faceInt: false },
    SE4: { rotation: 90, faceInt: false },
    SE5: { rotation: 0, faceInt: true },
    SE6: { rotation: 180, faceInt: true },
    SE7: { rotation: 270, faceInt: true },
    SE8: { rotation: 90, faceInt: true },
  };
  return map[se];
}

// ---------------------------------------------------------------------------
// VUE A — plaque (vue de face), compacte et centrée
// ---------------------------------------------------------------------------

function VuePlaque({
  config,
  laizeEtiqMm,
  devEtiqMm,
}: Props) {
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
        Vue A — plaque (vue de dessous, sens machine)
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
            VUE A = vue DE DESSOUS de la plaque (point de vue de la matière
            qui passe sous le cylindre). Le A est donc rendu à 180° pour que
            l'observateur voie ce qu'il verrait s'il regardait sous la
            presse — convention métier flexo. */}
        {Array.from({ length: config.nb_poses_dev }).map((_, row) =>
          Array.from({ length: config.nb_poses_laize }).map((__, col) => {
            const px = ox + chuteW + col * poseW;
            const py = oy + row * poseH;
            const cxA = px + poseW / 2;
            const cyA = py + poseH / 2;
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
                <g transform={`translate(${cxA} ${cyA}) rotate(180)`}>
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

function VueBobine({ config }: { config: OptimisationConfigOut }) {
  const { rotation, faceInt } = parseSE(config.sens_enroulement);
  const VBW = 480;
  const VBH = 280;

  // Bobine vue de FACE (de profil sur l'axe horizontal de la machine).
  //   - Sens extérieur (SE1-4) : bobine à gauche, liner sortant à droite avec
  //     les étiquettes bleu clair (face imprimée vers l'observateur).
  //   - Sens intérieur (SE5-8) : bobine à droite, liner sortant à gauche, et
  //     les étiquettes apparaissent JAUNI parce que le liner siliconé
  //     translucide passe par-dessus (convention atelier flexo).
  const cxBobine = faceInt ? VBW - 110 : 110;
  const cyBobine = 130;
  const rBobine = 80;
  const rMandrin = 22;

  // Liner sortant tangent à la bobine, du côté opposé au centre
  const linerY = cyBobine - 26;
  const linerH = 52;
  const linerStartX = faceInt ? 30 : cxBobine + rBobine - 4;
  const linerEndX = faceInt ? cxBobine - rBobine + 4 : VBW - 30;
  const linerLen = linerEndX - linerStartX;

  const NB_ETIQ = 3;
  const etiqGap = 5;
  const etiqW = (linerLen - 20 - etiqGap * (NB_ETIQ - 1)) / NB_ETIQ;
  const etiqH = linerH - 12;
  const etiqYTop = linerY + 6;

  // Couleurs étiquettes : bleu pour ext, jaune-liner pour int
  const etiqFill = faceInt ? COULEUR_ETIQ_INT : COULEUR_BLEU_CLAIR;
  const etiqStroke = faceInt ? COULEUR_ETIQ_INT_BORDURE : COULEUR_BLEU;
  const aFill = faceInt ? COULEUR_GRIS_FONCE : COULEUR_BLEU;

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue B — bobine livrée (vue de face)
      </figcaption>
      <svg
        viewBox={`0 0 ${VBW} ${VBH}`}
        width="100%"
        className="font-sans"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <radialGradient id="grad-bobine-face" cx="35%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#F9FAFB" />
            <stop offset="70%" stopColor="#E5E7EB" />
            <stop offset="100%" stopColor="#9CA3AF" />
          </radialGradient>
          <pattern
            id="liner-dots-b2"
            patternUnits="userSpaceOnUse"
            width={8}
            height={8}
          >
            <circle cx={2} cy={2} r={0.6} fill={COULEUR_HACHURE} />
          </pattern>
          <marker
            id="arrow-bleu-b2"
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

        {/* Bobine vue de face : cercle plein avec ombre douce */}
        <circle
          cx={cxBobine}
          cy={cyBobine}
          r={rBobine}
          fill="url(#grad-bobine-face)"
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={1}
        />
        {/* Quelques arcs concentriques pour suggérer les couches enroulées */}
        {[0.85, 0.7, 0.55, 0.4].map((f, i) => (
          <circle
            key={i}
            cx={cxBobine}
            cy={cyBobine}
            r={rBobine * f}
            fill="none"
            stroke={COULEUR_HACHURE}
            strokeWidth={0.5}
            strokeDasharray="2 3"
            opacity={0.5}
          />
        ))}
        {/* Mandrin au centre (vue de face : cercle plus foncé) */}
        <circle
          cx={cxBobine}
          cy={cyBobine}
          r={rMandrin}
          fill="#9CA3AF"
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.8}
        />
        <circle
          cx={cxBobine}
          cy={cyBobine}
          r={rMandrin * 0.55}
          fill="#4B5563"
          stroke="none"
        />
        <text
          x={cxBobine}
          y={cyBobine + 3}
          textAnchor="middle"
          fontSize={8}
          fontWeight={600}
          fill="white"
        >
          mandrin
        </text>

        {/* Repère START orange tangent au cercle (en haut) */}
        <g
          transform={`translate(${cxBobine + (faceInt ? -rBobine : rBobine) * 0.7}, ${cyBobine - rBobine + 6})`}
        >
          <rect
            x={-5}
            y={-5}
            width={10}
            height={10}
            fill={COULEUR_ORANGE}
            stroke="white"
            strokeWidth={0.5}
          />
          <text
            x={faceInt ? -10 : 10}
            y={4}
            fontSize={9}
            fontWeight={700}
            fill={COULEUR_ORANGE}
            textAnchor={faceInt ? "end" : "start"}
          >
            START
          </text>
        </g>

        {/* Liner sortant tangent (rectangle horizontal beige) */}
        <rect
          x={linerStartX}
          y={linerY}
          width={linerLen}
          height={linerH}
          fill={COULEUR_LINER}
          stroke={COULEUR_HACHURE}
          strokeWidth={0.6}
        />
        <rect
          x={linerStartX}
          y={linerY}
          width={linerLen}
          height={linerH}
          fill="url(#liner-dots-b2)"
          opacity={0.5}
        />

        {/* 3 étiquettes sur le liner (couleur jaune si sens intérieur) */}
        {Array.from({ length: NB_ETIQ }).map((_, i) => {
          // Index de la dernière étiquette = celle "qui sort" de la bobine
          // (proche du bord libre du liner, donc côté droit en ext, côté
          // gauche en int).
          const orderIdx = faceInt ? NB_ETIQ - 1 - i : i;
          const px = linerStartX + 10 + orderIdx * (etiqW + etiqGap);
          const isFurthest = i === NB_ETIQ - 1; // la + éloignée de la bobine
          return (
            <g key={i}>
              <rect
                x={px}
                y={etiqYTop}
                width={etiqW}
                height={etiqH}
                fill={etiqFill}
                stroke={etiqStroke}
                strokeWidth={0.7}
              />
              {isFurthest && (
                <g
                  transform={`translate(${px + etiqW / 2} ${etiqYTop + etiqH / 2}) rotate(${rotation})`}
                >
                  <text
                    x={0}
                    y={0}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={etiqH * 0.6}
                    fontWeight={700}
                    fill={aFill}
                  >
                    A
                  </text>
                </g>
              )}
            </g>
          );
        })}

        {/* Flèche déroulement au-dessus du liner */}
        <g>
          {faceInt ? (
            <line
              x1={linerEndX - 6}
              y1={linerY - 14}
              x2={linerStartX + 10}
              y2={linerY - 14}
              stroke={COULEUR_BLEU}
              strokeWidth={1.4}
              markerEnd="url(#arrow-bleu-b2)"
            />
          ) : (
            <line
              x1={linerStartX + 6}
              y1={linerY - 14}
              x2={linerEndX - 10}
              y2={linerY - 14}
              stroke={COULEUR_BLEU}
              strokeWidth={1.4}
              markerEnd="url(#arrow-bleu-b2)"
            />
          )}
          <text
            x={(linerStartX + linerEndX) / 2}
            y={linerY - 18}
            textAnchor="middle"
            fontSize={9}
            fontWeight={600}
            fill={COULEUR_BLEU}
          >
            Sens de déroulement
          </text>
        </g>

        {/* Cote ø bobine sous le cercle */}
        <line
          x1={cxBobine - rBobine}
          y1={cyBobine + rBobine + 15}
          x2={cxBobine + rBobine}
          y2={cyBobine + rBobine + 15}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line
          x1={cxBobine - rBobine}
          y1={cyBobine + rBobine + 10}
          x2={cxBobine - rBobine}
          y2={cyBobine + rBobine + 20}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <line
          x1={cxBobine + rBobine}
          y1={cyBobine + rBobine + 10}
          x2={cxBobine + rBobine}
          y2={cyBobine + rBobine + 20}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={cxBobine}
          y={cyBobine + rBobine + 32}
          textAnchor="middle"
          fontSize={11}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          Ø Diamètre Total Bobine {config.diametre_bobine_mm} mm
        </text>
        <text
          x={cxBobine}
          y={cyBobine + rBobine + 45}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_GRIS_FONCE}
        >
          Ø Mandrin (saisi dans le formulaire)
        </text>

        {/* Badge SE en haut */}
        <g transform="translate(18, 22)">
          <rect
            x={0}
            y={0}
            width={150}
            height={36}
            rx={5}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.6}
          />
          <text
            x={75}
            y={15}
            textAnchor="middle"
            fontSize={12}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            {senseAffichage(config.sens_enroulement)}
          </text>
          <text x={75} y={28} textAnchor="middle" fontSize={8} fill={COULEUR_BLEU}>
            {labelSE(config.sens_enroulement).split(" — ")[1] ?? ""}
          </text>
        </g>

        {/* Note "liner par-dessus" pour les sens intérieur */}
        {faceInt && (
          <text
            x={(linerStartX + linerEndX) / 2}
            y={linerY + linerH + 18}
            textAnchor="middle"
            fontSize={9}
            fontStyle="italic"
            fill={COULEUR_ETIQ_INT_BORDURE}
          >
            étiquettes vues à travers le liner siliconé (face dedans)
          </text>
        )}
      </svg>
    </figure>
  );
}

function labelSE(se: SensEnroulement): string {
  const map: Record<SensEnroulement, string> = {
    SE1: "Sens 1 — 0° Extérieur droite avant",
    SE2: "Sens 2 — 180° Extérieur gauche avant",
    SE3: "Sens 3 — 270° Extérieur pied avant",
    SE4: "Sens 4 — 90° Extérieur tête avant",
    SE5: "Sens 5 — 0° Intérieur droite avant",
    SE6: "Sens 6 — 180° Intérieur gauche avant",
    SE7: "Sens 7 — 270° Intérieur pied avant",
    SE8: "Sens 8 — 90° Intérieur tête avant",
  };
  return map[se];
}

function senseAffichage(se: SensEnroulement): string {
  const n = parseInt(se.replace("SE", ""), 10);
  return `Sens ${n}`;
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
  const { faceInt } = parseSE(config.sens_enroulement);
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
        Laize liner {config.laize_liner_mm} mm ·{" "}
        {labelSE(config.sens_enroulement)} · ml total {config.ml_total_m} m
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

        {Array.from({ length: NB_ETIQ_AFFICHEES }).map((_, i) => {
          const px = ox + i * (etiqW + intervalleDevUnits);
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
              <text
                x={px + etiqW / 2}
                y={oy + etiqH / 2}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={etiqH * 0.5}
                fontWeight={700}
                fill={aFill}
              >
                A
              </text>
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
