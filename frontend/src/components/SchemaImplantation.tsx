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
        Vue A — plaque (vue de face)
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

        {/* Grille des poses */}
        {Array.from({ length: config.nb_poses_dev }).map((_, row) =>
          Array.from({ length: config.nb_poses_laize }).map((__, col) => {
            const px = ox + chuteW + col * poseW;
            const py = oy + row * poseH;
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
                <text
                  x={px + poseW / 2}
                  y={py + poseH / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={Math.min(poseW, poseH) * 0.42}
                  fontWeight={700}
                  fill={COULEUR_BLEU}
                >
                  A
                </text>
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
          Laize papier {config.laize_papier_mm} mm
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

        {/* Cotes chute */}
        <text
          x={ox + chuteW / 2}
          y={oy + innerH + 42}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_GRIS}
        >
          chute {config.chute_laterale_reelle_mm}
        </text>
        <text
          x={ox + widthPapier - chuteW / 2}
          y={oy + innerH + 42}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_GRIS}
        >
          chute {config.chute_laterale_reelle_mm}
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

        {/* Cotes intervalles (orange pointillé) */}
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
              int. laize {config.intervalle_laize_reel_mm}
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
              int. dev {config.intervalle_dev_reel_mm}
            </text>
          </g>
        )}

        {/* Flèche défilement à gauche */}
        <g transform={`translate(${ox - 35}, ${oy + innerH / 2})`}>
          <line
            x1={0}
            y1={-25}
            x2={0}
            y2={25}
            stroke={COULEUR_BLEU}
            strokeWidth={1.5}
            markerEnd="url(#arrow-bleu-a)"
          />
          <text
            x={-8}
            y={0}
            fontSize={9}
            fontWeight={600}
            fill={COULEUR_BLEU}
            textAnchor="middle"
            transform="rotate(-90)"
          >
            défilement
          </text>
        </g>

        {/* Légende dimensions */}
        <text
          x={VBW / 2}
          y={VBH - 10}
          textAnchor="middle"
          fontSize={10}
          fill={COULEUR_GRIS_FONCE}
          fontStyle="italic"
        >
          Étiquette laize {laizeEtiqMm} × dev {devEtiqMm} mm — {config.nb_poses_laize}{" "}
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
  const VBW = 460;
  const VBH = 260;

  // Pour "face intérieur" on inverse horizontalement toute la vue (la bobine
  // se retrouve à droite et le liner sort vers la gauche).
  const flipGroup = faceInt ? `translate(${VBW} 0) scale(-1 1)` : "";

  // Géométrie : bobine cylindrique à gauche (rectangle vertical ombré + 2
  // ellipses pour les faces avant/arrière), mandrin au centre, liner
  // horizontal sortant vers la droite, 3 étiquettes posées dessus avec un A
  // tourné selon le sens d'enroulement dans la DERNIÈRE étiquette.
  const cxBobine = 110;
  const cyBobine = 130;
  const rxBobine = 60;
  const ryBobine = 85;
  const rxMandrin = 22;
  const ryMandrin = 26;

  const linerY = cyBobine - 28;
  const linerH = 56;
  const linerStartX = cxBobine + 18;
  const linerEndX = VBW - 30;
  const linerLen = linerEndX - linerStartX;

  const NB_ETIQ = 3;
  const etiqGap = 4;
  const etiqW = (linerLen - 24 - etiqGap * (NB_ETIQ - 1)) / NB_ETIQ;
  const etiqH = linerH - 14;
  const etiqYTop = linerY + 7;

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue B — bobine livrée
      </figcaption>
      <svg
        viewBox={`0 0 ${VBW} ${VBH}`}
        width="100%"
        className="font-sans"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="grad-bobine-b" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#D1D5DB" />
            <stop offset="50%" stopColor="#F3F4F6" />
            <stop offset="100%" stopColor="#9CA3AF" />
          </linearGradient>
          <pattern
            id="liner-dots-b"
            patternUnits="userSpaceOnUse"
            width={8}
            height={8}
          >
            <circle cx={2} cy={2} r={0.6} fill={COULEUR_HACHURE} />
          </pattern>
          <marker
            id="arrow-bleu-b"
            viewBox="0 0 10 10"
            refX={9}
            refY={5}
            markerWidth={8}
            markerHeight={8}
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={COULEUR_BLEU} />
          </marker>
        </defs>

        <g transform={flipGroup}>
          {/* Tube cylindrique vu de profil (bobine pleine) */}
          {/* Côté arrière (rectangle ombré) */}
          <rect
            x={cxBobine - rxBobine + 8}
            y={cyBobine - ryBobine}
            width={(rxBobine - 8) * 2}
            height={ryBobine * 2}
            fill="url(#grad-bobine-b)"
            stroke="none"
          />
          {/* Côté gauche (ellipse face) */}
          <ellipse
            cx={cxBobine - rxBobine + 8}
            cy={cyBobine}
            rx={8}
            ry={ryBobine}
            fill="#D1D5DB"
            stroke={COULEUR_GRIS_FONCE}
            strokeWidth={0.8}
          />
          {/* Côté droit (ellipse arrière, visible en perspective légère) */}
          <ellipse
            cx={cxBobine + rxBobine}
            cy={cyBobine}
            rx={8}
            ry={ryBobine}
            fill="#F3F4F6"
            stroke={COULEUR_GRIS_FONCE}
            strokeWidth={0.8}
          />

          {/* Bord supérieur et inférieur du tube */}
          <line
            x1={cxBobine - rxBobine + 8}
            y1={cyBobine - ryBobine}
            x2={cxBobine + rxBobine}
            y2={cyBobine - ryBobine}
            stroke={COULEUR_GRIS_FONCE}
            strokeWidth={0.8}
          />
          <line
            x1={cxBobine - rxBobine + 8}
            y1={cyBobine + ryBobine}
            x2={cxBobine + rxBobine}
            y2={cyBobine + ryBobine}
            stroke={COULEUR_GRIS_FONCE}
            strokeWidth={0.8}
          />

          {/* Mandrin (vue de profil : ovale au centre du flanc droit) */}
          <ellipse
            cx={cxBobine + rxBobine}
            cy={cyBobine}
            rx={6}
            ry={ryMandrin}
            fill="#6B7280"
            stroke={COULEUR_GRIS_FONCE}
            strokeWidth={0.6}
          />
          <ellipse
            cx={cxBobine + rxBobine}
            cy={cyBobine}
            rx={3}
            ry={ryMandrin * 0.6}
            fill="#374151"
            stroke="none"
          />

          {/* Repère START orange en surface */}
          <g transform={`translate(${cxBobine + rxBobine + 2}, ${cyBobine - ryBobine + 12})`}>
            <rect x={-5} y={-5} width={10} height={10} fill={COULEUR_ORANGE} stroke="white" strokeWidth={0.4} />
            <text x={14} y={4} fontSize={9} fontWeight={700} fill={COULEUR_ORANGE}>
              START
            </text>
          </g>

          {/* Liner sortant (rectangle horizontal beige) */}
          <rect
            x={linerStartX}
            y={linerY}
            width={linerEndX - linerStartX}
            height={linerH}
            fill={COULEUR_LINER}
            stroke={COULEUR_HACHURE}
            strokeWidth={0.6}
          />
          <rect
            x={linerStartX}
            y={linerY}
            width={linerEndX - linerStartX}
            height={linerH}
            fill="url(#liner-dots-b)"
            opacity={0.5}
          />

          {/* 3 étiquettes sur le liner */}
          {Array.from({ length: NB_ETIQ }).map((_, i) => {
            const px = linerStartX + 12 + i * (etiqW + etiqGap);
            const isLast = i === NB_ETIQ - 1;
            return (
              <g key={i}>
                <rect
                  x={px}
                  y={etiqYTop}
                  width={etiqW}
                  height={etiqH}
                  fill={COULEUR_BLEU_CLAIR}
                  stroke={COULEUR_BLEU}
                  strokeWidth={0.7}
                />
                {/* Le A apparaît uniquement dans la dernière étiquette
                     (convention image Eric : on voit le sens du A "en sortie"
                     de la bobine). Les 2 premières sont vides pour
                     symboliser la continuité du tirage. */}
                {isLast && (
                  <g
                    transform={
                      // Compense le flip horizontal pour que le A garde son
                      // sens lisible côté observateur même quand toute la
                      // vue est inversée.
                      `translate(${px + etiqW / 2} ${etiqYTop + etiqH / 2}) ` +
                      (faceInt ? "scale(-1 1) " : "") +
                      `rotate(${rotation})`
                    }
                  >
                    <text
                      x={0}
                      y={0}
                      textAnchor="middle"
                      dominantBaseline="central"
                      fontSize={etiqH * 0.65}
                      fontWeight={700}
                      fill={COULEUR_BLEU}
                    >
                      A
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Flèche défilement au-dessus du liner */}
          <line
            x1={linerStartX + 6}
            y1={linerY - 12}
            x2={linerEndX - 10}
            y2={linerY - 12}
            stroke={COULEUR_BLEU}
            strokeWidth={1.2}
            markerEnd="url(#arrow-bleu-b)"
          />
          <text
            x={(linerStartX + linerEndX) / 2}
            y={linerY - 16}
            textAnchor="middle"
            fontSize={9}
            fontWeight={600}
            fill={COULEUR_BLEU}
          >
            déroulement
          </text>
        </g>

        {/* Cote ø bobine (sous la bobine, NON flippée pour rester lisible) */}
        <g transform={faceInt ? `translate(${VBW - cxBobine * 2} 0)` : ""}>
          <line
            x1={cxBobine - rxBobine + 8}
            y1={cyBobine + ryBobine + 14}
            x2={cxBobine + rxBobine}
            y2={cyBobine + ryBobine + 14}
            stroke={COULEUR_BLEU}
            strokeWidth={0.8}
          />
          <text
            x={cxBobine + 4}
            y={cyBobine + ryBobine + 28}
            textAnchor="middle"
            fontSize={10}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            ø {config.diametre_bobine_mm} mm
          </text>
          <text
            x={cxBobine + 4}
            y={cyBobine + ryBobine + 40}
            textAnchor="middle"
            fontSize={8}
            fill={COULEUR_GRIS_FONCE}
          >
            mandrin ({rxMandrin * 2}×{ryMandrin * 2} schématique)
          </text>
        </g>

        {/* Badge SE en haut-gauche */}
        <g transform="translate(18, 22)">
          <rect
            x={0}
            y={0}
            width={140}
            height={36}
            rx={5}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.6}
          />
          <text x={70} y={15} textAnchor="middle" fontSize={12} fontWeight={700} fill={COULEUR_BLEU}>
            {config.sens_enroulement}
          </text>
          <text x={70} y={28} textAnchor="middle" fontSize={9} fill={COULEUR_BLEU}>
            {labelSE(config.sens_enroulement)}
          </text>
        </g>

        {/* Cote laize liner (à droite du liner) */}
        <text
          x={VBW - 30}
          y={cyBobine + ryBobine + 28}
          textAnchor="end"
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
        >
          laize liner {config.laize_liner_mm} mm
        </text>
      </svg>
    </figure>
  );
}

function labelSE(se: SensEnroulement): string {
  const map: Record<SensEnroulement, string> = {
    SE1: "0° extérieur",
    SE2: "180° extérieur",
    SE3: "270° extérieur",
    SE4: "90° extérieur",
    SE5: "0° intérieur",
    SE6: "180° intérieur",
    SE7: "270° intérieur",
    SE8: "90° intérieur",
  };
  return map[se];
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

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue C — bobine fille déroulée chez le client
      </figcaption>
      <p className="text-xs text-muted-foreground">
        Laize liner {config.laize_liner_mm} mm · sens enroulement{" "}
        {config.sens_enroulement} · ml total {config.ml_total_m} m
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
                fill={COULEUR_BLEU_CLAIR}
                stroke={COULEUR_BLEU}
                strokeWidth={0.8}
              />
              <text
                x={px + etiqW / 2}
                y={oy + etiqH / 2}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={etiqH * 0.5}
                fontWeight={700}
                fill={COULEUR_BLEU}
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
          int. dev {config.intervalle_dev_reel_mm}
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
