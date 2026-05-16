"use client";

import { type OptimisationConfigOut } from "@/lib/api";

/**
 * Schéma BAT (Bon À Tirer) — PR #9.1 MVP.
 *
 * 3 vues complémentaires rendues en SVG inline, viewBox responsive :
 *   A. Plaque vue de face   — laize papier + chutes + plaque + poses grille
 *   B. Bobine vue de face   — couches enroulées + mandrin + repère A
 *   C. Bobine fille (client) — bande liner + étiquettes alignées
 *
 * Conventions visuelles :
 *   - Bleu primaire #0C447C (étiquette imprimée, cotes principales)
 *   - Orange #993C1D (intervalles, repères de découpe)
 *   - Liner #FAF7EE avec hachures #C8C6BC
 *   - Couleurs custom inline (cohérent avec stack Tailwind shadcn sans
 *     ajouter de CSS variables custom).
 *
 * PR 9.2 (Sprint 14) ajoutera : repères de coupe, fond perdu, marge
 * sécurité textes, spots détection, variantes SE1-4 (rotation/miroir
 * du A), pré-découpe. PR 9.3 ajoutera : header BAT, infos projet,
 * légende, zone signature, PDF.
 */

const COULEUR_BLEU = "#0C447C";
const COULEUR_BLEU_CLAIR = "#DCE7F3";
const COULEUR_ORANGE = "#993C1D";
const COULEUR_GRIS_FONCE = "#374151";
const COULEUR_GRIS = "#9CA3AF";
const COULEUR_GRIS_CLAIR = "#D1D5DB";
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
// VUE A — plaque (vue de face)
// ---------------------------------------------------------------------------

function VuePlaque({
  config,
  laizeEtiqMm,
  devEtiqMm,
}: Props) {
  // SVG viewBox en "unités schéma" — pas en mm pour permettre la responsivité.
  // On normalise la largeur à 400 unités et on en déduit la hauteur.
  const VBW = 460; // viewBox width
  // Hauteur : Z cylindre dimensionne le visuel + marges pour cotes
  const ratio = config.z_cylindre_mm / config.laize_papier_mm;
  const innerW = 360; // largeur utile (sans cotes)
  const innerH = innerW * ratio;
  const VBH = innerH + 120;

  // Origin de la plaque (haut-gauche dans la viewBox)
  const ox = 50;
  const oy = 60;
  const widthPapier = innerW;
  const widthPlaque =
    (config.laize_plaque_mm / config.laize_papier_mm) * innerW;
  const chuteW = (widthPapier - widthPlaque) / 2;

  // Pose : grille nb_poses_laize × nb_poses_dev sur la zone plaque
  const poseW = widthPlaque / config.nb_poses_laize;
  const poseH = innerH / config.nb_poses_dev;
  const intervalleLaizeUnits =
    (config.intervalle_laize_reel_mm / config.laize_papier_mm) * innerW;
  const intervalleDevUnits =
    (config.intervalle_dev_reel_mm / config.z_cylindre_mm) * innerH;
  const etiqW = poseW - intervalleLaizeUnits * ((config.nb_poses_laize - 1) /
    config.nb_poses_laize);
  void etiqW; // Conservée pour PR 9.2 (marges fond perdu / sécurité)

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue A — plaque (vue de face)
      </figcaption>
      <svg
        viewBox={`0 0 ${VBW} ${VBH}`}
        width="100%"
        className="font-sans"
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
        </defs>

        {/* Cadre laize papier (pointillé beige) */}
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

        {/* Plaque imprimée (bordure pleine) */}
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
                  x={px + 2}
                  y={py + 2}
                  width={poseW - 4}
                  height={poseH - 4}
                  fill={COULEUR_BLEU_CLAIR}
                  stroke={COULEUR_BLEU}
                  strokeWidth={0.4}
                />
                <text
                  x={px + poseW / 2}
                  y={py + poseH / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={Math.min(poseW, poseH) * 0.45}
                  fontWeight={700}
                  fill={COULEUR_BLEU}
                >
                  A
                </text>
              </g>
            );
          })
        )}

        {/* Cote laize papier (haut, gras, englobant la plaque) */}
        <line
          x1={ox}
          y1={oy - 25}
          x2={ox + widthPapier}
          y2={oy - 25}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line x1={ox} y1={oy - 30} x2={ox} y2={oy} stroke={COULEUR_BLEU} strokeWidth={0.4} />
        <line
          x1={ox + widthPapier}
          y1={oy - 30}
          x2={ox + widthPapier}
          y2={oy}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={ox + widthPapier / 2}
          y={oy - 30}
          textAnchor="middle"
          fontSize={10}
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
          y={oy + innerH + 28}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_GRIS_FONCE}
        >
          Laize plaque {config.laize_plaque_mm} mm
        </text>

        {/* Cote chute latérale (chaque côté) */}
        <text
          x={ox + chuteW / 2}
          y={oy + innerH + 50}
          textAnchor="middle"
          fontSize={8}
          fill={COULEUR_GRIS}
        >
          chute {config.chute_laterale_reelle_mm}
        </text>
        <text
          x={ox + widthPapier - chuteW / 2}
          y={oy + innerH + 50}
          textAnchor="middle"
          fontSize={8}
          fill={COULEUR_GRIS}
        >
          chute {config.chute_laterale_reelle_mm}
        </text>

        {/* Cote Z cylindre (droite, verticale) */}
        <line
          x1={ox + widthPapier + 18}
          y1={oy}
          x2={ox + widthPapier + 18}
          y2={oy + innerH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line
          x1={ox + widthPapier + 13}
          y1={oy}
          x2={ox + widthPapier + 23}
          y2={oy}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <line
          x1={ox + widthPapier + 13}
          y1={oy + innerH}
          x2={ox + widthPapier + 23}
          y2={oy + innerH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={ox + widthPapier + 24}
          y={oy + innerH / 2}
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_BLEU}
          dominantBaseline="middle"
        >
          Z cyl {config.z_cylindre_mm} mm
        </text>

        {/* Cotes intervalles (orange pointillé) */}
        {config.nb_poses_laize > 1 && (
          <g>
            <line
              x1={ox + chuteW + poseW - intervalleLaizeUnits / 2}
              y1={oy - 5}
              x2={ox + chuteW + poseW + intervalleLaizeUnits / 2}
              y2={oy - 5}
              stroke={COULEUR_ORANGE}
              strokeWidth={0.6}
              strokeDasharray="2 1"
            />
            <text
              x={ox + chuteW + poseW}
              y={oy - 8}
              textAnchor="middle"
              fontSize={8}
              fill={COULEUR_ORANGE}
            >
              int. laize {config.intervalle_laize_reel_mm}
            </text>
          </g>
        )}
        {config.nb_poses_dev > 1 && (
          <g>
            <line
              x1={ox - 5}
              y1={oy + poseH - intervalleDevUnits / 2}
              x2={ox - 5}
              y2={oy + poseH + intervalleDevUnits / 2}
              stroke={COULEUR_ORANGE}
              strokeWidth={0.6}
              strokeDasharray="2 1"
            />
            <text
              x={ox - 8}
              y={oy + poseH}
              textAnchor="end"
              fontSize={8}
              fill={COULEUR_ORANGE}
              dominantBaseline="middle"
            >
              int. dev {config.intervalle_dev_reel_mm}
            </text>
          </g>
        )}

        {/* Flèche défilement (gauche, bleue) */}
        <g transform={`translate(${ox - 30}, ${oy + innerH / 2})`}>
          <line x1={0} y1={-20} x2={0} y2={20} stroke={COULEUR_BLEU} strokeWidth={1} />
          <polygon points="-3,15 3,15 0,22" fill={COULEUR_BLEU} />
          <text
            x={-12}
            y={0}
            fontSize={8}
            fill={COULEUR_BLEU}
            textAnchor="middle"
            transform="rotate(-90)"
          >
            défilement
          </text>
        </g>

        {/* Légende dimensions étiquette en bas */}
        <text
          x={ox + widthPapier / 2}
          y={VBH - 8}
          textAnchor="middle"
          fontSize={8}
          fill={COULEUR_GRIS_FONCE}
          fontStyle="italic"
        >
          Étiquette laize {laizeEtiqMm} × dev {devEtiqMm} mm
        </text>
      </svg>
    </figure>
  );
}

// ---------------------------------------------------------------------------
// VUE B — bobine (vue de face)
// ---------------------------------------------------------------------------

function VueBobine({ config }: { config: OptimisationConfigOut }) {
  const VBW = 320;
  const VBH = 320;
  const cx = VBW / 2;
  const cy = VBH / 2 - 10;
  const rBobine = 100;
  // Le ratio mandrin/bobine vient de la prod réelle : ø~70-180 mandrin
  // pour ø~250-300 bobine → ratio ~0.3. On garde un visuel cohérent et
  // pas un cercle quasi-plein.
  const rMandrin = Math.max(20, rBobine * 0.25);

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue B — bobine (vue de face)
      </figcaption>
      <svg viewBox={`0 0 ${VBW} ${VBH}`} width="100%" className="font-sans">
        {/* Bobine extérieur */}
        <circle
          cx={cx}
          cy={cy}
          r={rBobine}
          fill={COULEUR_BLEU_CLAIR}
          stroke={COULEUR_BLEU}
          strokeWidth={1}
        />
        {/* 3 couches concentriques pointillées (matière enroulée) */}
        {[0.85, 0.7, 0.55].map((f, i) => (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={rBobine * f}
            fill="none"
            stroke={COULEUR_GRIS_CLAIR}
            strokeWidth={0.4}
            strokeDasharray="2 2"
          />
        ))}
        {/* Mandrin */}
        <circle
          cx={cx}
          cy={cy}
          r={rMandrin}
          fill="white"
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={1}
        />
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={9}
          fill={COULEUR_GRIS_FONCE}
        >
          mandrin
        </text>

        {/* Petit rectangle bleu en haut (couche externe) avec "A" — SE1 par défaut */}
        <g transform={`translate(${cx}, ${cy - rBobine + 5})`}>
          <rect
            x={-10}
            y={-10}
            width={20}
            height={20}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.4}
          />
          <text
            x={0}
            y={0}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={11}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            A
          </text>
        </g>

        {/* Flèche enroulement (arc à droite) */}
        <g>
          <path
            d={`M ${cx + rBobine + 10} ${cy - 30} A 40 40 0 0 1 ${cx + rBobine + 10} ${cy + 30}`}
            fill="none"
            stroke={COULEUR_BLEU}
            strokeWidth={0.8}
          />
          <polygon
            points={`${cx + rBobine + 10},${cy + 30} ${cx + rBobine + 4},${cy + 25} ${cx + rBobine + 4},${cy + 35}`}
            fill={COULEUR_BLEU}
          />
          <text
            x={cx + rBobine + 30}
            y={cy}
            fontSize={9}
            fill={COULEUR_BLEU}
            dominantBaseline="middle"
          >
            Enroulement →
          </text>
        </g>

        {/* Cote ø bobine (horizontale en bas) */}
        <line
          x1={cx - rBobine}
          y1={cy + rBobine + 20}
          x2={cx + rBobine}
          y2={cy + rBobine + 20}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line
          x1={cx - rBobine}
          y1={cy + rBobine + 15}
          x2={cx - rBobine}
          y2={cy + rBobine + 25}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <line
          x1={cx + rBobine}
          y1={cy + rBobine + 15}
          x2={cx + rBobine}
          y2={cy + rBobine + 25}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={cx}
          y={cy + rBobine + 35}
          textAnchor="middle"
          fontSize={10}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          ø bobine {config.diametre_bobine_mm} mm
        </text>

        {/* Sens d'enroulement (texte) */}
        <text
          x={10}
          y={20}
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
        >
          {config.sens_enroulement}
        </text>

        {/* Cote ø mandrin (texte interne) */}
        <text
          x={cx}
          y={cy + rMandrin + 12}
          textAnchor="middle"
          fontSize={7}
          fill={COULEUR_GRIS}
        >
          mandrin
        </text>
      </svg>
    </figure>
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
  const VBW = 720;
  const VBH = 220;
  const NB_ETIQ_AFFICHEES = 5;
  const ox = 50;
  const oy = 50;
  const innerW = VBW - 100;

  // Largeur d'une étiquette + intervalle dev (proportions schématiques)
  const intervalleDevUnits = (innerW / NB_ETIQ_AFFICHEES) * 0.08;
  const etiqW = (innerW - intervalleDevUnits * (NB_ETIQ_AFFICHEES - 1)) /
    NB_ETIQ_AFFICHEES;
  // Hauteur étiquette : proportion laize / dev
  const aspectEtiq = laizeEtiqMm / devEtiqMm;
  const etiqH = etiqW * aspectEtiq;
  const linerH = etiqH + 16; // marge liner schématique

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue bobine fille — déroulée chez le client
      </figcaption>
      <p className="text-xs text-muted-foreground">
        Laize liner {config.laize_liner_mm} mm · sens enroulement{" "}
        {config.sens_enroulement}
      </p>
      <svg viewBox={`0 0 ${VBW} ${VBH}`} width="100%" className="font-sans">
        <defs>
          <pattern
            id="liner-dots"
            patternUnits="userSpaceOnUse"
            width={8}
            height={8}
          >
            <circle cx={2} cy={2} r={0.6} fill={COULEUR_HACHURE} />
          </pattern>
        </defs>

        {/* Bande liner */}
        <rect
          x={ox}
          y={oy - 8}
          width={innerW}
          height={linerH}
          fill={COULEUR_LINER}
          stroke={COULEUR_HACHURE}
          strokeWidth={0.5}
        />
        <rect
          x={ox}
          y={oy - 8}
          width={innerW}
          height={linerH}
          fill="url(#liner-dots)"
          opacity={0.5}
        />

        {/* 5 étiquettes alignées */}
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
                strokeWidth={0.6}
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

        {/* Cote dev étiquette (au-dessus de la première) */}
        <line
          x1={ox}
          y1={oy - 18}
          x2={ox + etiqW}
          y2={oy - 18}
          stroke={COULEUR_BLEU}
          strokeWidth={0.6}
        />
        <text
          x={ox + etiqW / 2}
          y={oy - 22}
          textAnchor="middle"
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_BLEU}
        >
          dev {devEtiqMm} mm
        </text>

        {/* Cote int. dev entre les 2 premières étiquettes */}
        <text
          x={ox + etiqW + intervalleDevUnits / 2}
          y={oy + etiqH + 22}
          textAnchor="middle"
          fontSize={8}
          fill={COULEUR_ORANGE}
        >
          int. dev {config.intervalle_dev_reel_mm}
        </text>

        {/* Cote laize étiquette à droite */}
        <line
          x1={VBW - 30}
          y1={oy}
          x2={VBW - 30}
          y2={oy + etiqH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.6}
        />
        <text
          x={VBW - 22}
          y={oy + etiqH / 2}
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_BLEU}
          dominantBaseline="middle"
        >
          laize {laizeEtiqMm}
        </text>

        {/* Cote laize liner à gauche */}
        <line
          x1={20}
          y1={oy - 8}
          x2={20}
          y2={oy - 8 + linerH}
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.6}
        />
        <text
          x={12}
          y={oy - 8 + linerH / 2}
          fontSize={9}
          fill={COULEUR_GRIS_FONCE}
          textAnchor="end"
          dominantBaseline="middle"
          transform={`rotate(-90 12 ${oy - 8 + linerH / 2})`}
        >
          liner {config.laize_liner_mm}
        </text>

        {/* Flèche défilement (bas) */}
        <g transform={`translate(${VBW / 2}, ${VBH - 30})`}>
          <line x1={-50} y1={0} x2={50} y2={0} stroke={COULEUR_BLEU} strokeWidth={1} />
          <polygon points="50,0 42,-4 42,4" fill={COULEUR_BLEU} />
          <text
            x={0}
            y={14}
            textAnchor="middle"
            fontSize={8}
            fill={COULEUR_BLEU}
          >
            Sens de défilement chez le client (machine de pose)
          </text>
        </g>
      </svg>

      {/* Légende */}
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
        <div className="text-right">
          Quantité : ml total {config.ml_total_m} m
        </div>
      </div>
    </figure>
  );
}
