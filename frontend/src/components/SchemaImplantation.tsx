"use client";

import { type OptimisationConfigOut } from "@/lib/api";

/**
 * Schéma BAT (Bon À Tirer) — PR #9.1 + retours Eric.
 *
 * 3 vues complémentaires rendues en SVG inline, viewBox responsive :
 *   A. Plaque vue de face   — laize papier + chutes + plaque + poses grille
 *   B. Bobine isométrique  — perspective 3D, bobine + liner sortant + 3 étiq
 *   C. Bobine fille (client) — bande liner + étiquettes alignées
 *
 * Couleurs métier (hardcodées inline, pas de CSS vars custom) :
 *   - Bleu primaire     #0C447C (étiquette imprimée, cotes principales)
 *   - Bleu clair        #DCE7F3 (remplissage étiquettes)
 *   - Orange            #993C1D (intervalles, repère start)
 *   - Liner             #FAF7EE / #C8C6BC (hachures)
 *   - Cylindre / mandrin gris #6B7280 / #9CA3AF (volume 3D)
 *
 * PR 9.2 (Sprint 14) ajoutera : repères de coupe, fond perdu, marges
 * sécurité textes, spots détection, application visuelle des SE1-4
 * (rotation/miroir du A) sur les 3 vues.
 */

const COULEUR_BLEU = "#0C447C";
const COULEUR_BLEU_CLAIR = "#DCE7F3";
const COULEUR_ORANGE = "#993C1D";
const COULEUR_GRIS_FONCE = "#374151";
const COULEUR_GRIS = "#9CA3AF";
const COULEUR_GRIS_CLAIR = "#D1D5DB";
const COULEUR_LINER = "#FAF7EE";
const COULEUR_HACHURE = "#C8C6BC";
const COULEUR_MANDRIN = "#6B7280";

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
        <VueBobineIsometrique config={config} />
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
  // viewBox dimensionné pour laisser largement la place aux cotes externes.
  // Largeur 520, on calcule la hauteur selon le ratio Z / laize_papier.
  const VBW = 520;
  const innerW = 380;
  const ratio = config.z_cylindre_mm / config.laize_papier_mm;
  const innerH = Math.min(Math.max(innerW * ratio, 180), 600);
  const VBH = innerH + 200;

  // Centrage horizontal du SVG dans la viewBox
  const ox = (VBW - innerW) / 2;
  const oy = 90;

  const widthPapier = innerW;
  const widthPlaque =
    (config.laize_plaque_mm / config.laize_papier_mm) * innerW;
  const chuteW = (widthPapier - widthPlaque) / 2;

  // Grille des poses sur la zone plaque
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
            id="arrow-bleu"
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

        {/* === BLOC IDENTITÉ CYLINDRE (en haut, voyant) === */}
        <g transform={`translate(${VBW / 2}, 30)`}>
          <rect
            x={-130}
            y={-22}
            width={260}
            height={44}
            rx={6}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.8}
          />
          <text
            x={0}
            y={-3}
            textAnchor="middle"
            fontSize={14}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            Cylindre {config.nb_dents_cylindre} dents
          </text>
          <text
            x={0}
            y={14}
            textAnchor="middle"
            fontSize={11}
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

        {/* Cote laize papier (au-dessus de la plaque, gras bleu) */}
        <line
          x1={ox}
          y1={oy - 25}
          x2={ox + widthPapier}
          y2={oy - 25}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line
          x1={ox}
          y1={oy - 30}
          x2={ox}
          y2={oy}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
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
          fontSize={11}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          Laize papier {config.laize_papier_mm} mm
        </text>

        {/* Cote laize plaque (sous la plaque, gris) */}
        <line
          x1={ox + chuteW}
          y1={oy + innerH + 18}
          x2={ox + chuteW + widthPlaque}
          y2={oy + innerH + 18}
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.6}
        />
        <text
          x={ox + chuteW + widthPlaque / 2}
          y={oy + innerH + 32}
          textAnchor="middle"
          fontSize={10}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
        >
          Laize plaque {config.laize_plaque_mm} mm
        </text>

        {/* Cotes chute latérale (gris léger, sous les bandes hachurées) */}
        <text
          x={ox + chuteW / 2}
          y={oy + innerH + 50}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_GRIS}
        >
          chute {config.chute_laterale_reelle_mm}
        </text>
        <text
          x={ox + widthPapier - chuteW / 2}
          y={oy + innerH + 50}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_GRIS}
        >
          chute {config.chute_laterale_reelle_mm}
        </text>

        {/* Cote Z cylindre à droite (cotation verticale) */}
        <line
          x1={ox + widthPapier + 28}
          y1={oy}
          x2={ox + widthPapier + 28}
          y2={oy + innerH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line
          x1={ox + widthPapier + 23}
          y1={oy}
          x2={ox + widthPapier + 33}
          y2={oy}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <line
          x1={ox + widthPapier + 23}
          y1={oy + innerH}
          x2={ox + widthPapier + 33}
          y2={oy + innerH}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={ox + widthPapier + 40}
          y={oy + innerH / 2 - 8}
          fontSize={10}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          Z {config.z_cylindre_mm}
        </text>
        <text
          x={ox + widthPapier + 40}
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
              y1={oy - 8}
              x2={ox + chuteW + poseW + intervalleLaizeUnits / 2}
              y2={oy - 8}
              stroke={COULEUR_ORANGE}
              strokeWidth={0.7}
              strokeDasharray="2 1"
            />
            <text
              x={ox + chuteW + poseW}
              y={oy - 11}
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
              x1={ox - 8}
              y1={oy + poseH - intervalleDevUnits / 2}
              x2={ox - 8}
              y2={oy + poseH + intervalleDevUnits / 2}
              stroke={COULEUR_ORANGE}
              strokeWidth={0.7}
              strokeDasharray="2 1"
            />
            <text
              x={ox - 12}
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

        {/* Flèche défilement à gauche, visible et agrandie */}
        <g transform={`translate(${ox - 50}, ${oy + innerH / 2})`}>
          <line
            x1={0}
            y1={-30}
            x2={0}
            y2={30}
            stroke={COULEUR_BLEU}
            strokeWidth={1.5}
            markerEnd="url(#arrow-bleu)"
          />
          <text
            x={-8}
            y={0}
            fontSize={10}
            fontWeight={600}
            fill={COULEUR_BLEU}
            textAnchor="middle"
            transform="rotate(-90)"
          >
            défilement
          </text>
        </g>

        {/* Légende dimensions étiquette en bas */}
        <text
          x={VBW / 2}
          y={VBH - 12}
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
// VUE B — bobine isométrique 3D (perspective)
// ---------------------------------------------------------------------------

function VueBobineIsometrique({ config }: { config: OptimisationConfigOut }) {
  // viewBox plus large que haut pour accueillir le liner sortant à droite
  const VBW = 520;
  const VBH = 340;

  // Bobine : 2 ellipses (face avant et arrière) reliées par 2 lignes
  // d'enveloppe. Mode isométrique simple : la face arrière est décalée
  // de (depth, -depth/2) par rapport à la face avant.
  const cxAv = 130; // centre face avant
  const cyAv = 200;
  const depthX = 70; // décalage face arrière vers la droite
  const depthY = -28; // et vers le haut (perspective iso)
  const cxAr = cxAv + depthX;
  const cyAr = cyAv + depthY;

  const rxBobine = 90;
  const ryBobine = 90;
  const rxMandrin = Math.max(18, rxBobine * 0.28);
  const ryMandrin = rxMandrin;

  // Liner sortant : trapèze qui part du haut de la bobine vers la droite,
  // légèrement incliné pour la perspective. Hauteur du liner = épaisseur
  // schématique.
  const linerY = cyAv - 60; // sortie tangente haut bobine
  const linerStartX = cxAv + 8;
  const linerEndX = VBW - 30;
  const linerHEpais = 38; // épaisseur visuelle du sandwich liner+étiq
  // Légère pente descendante (perspective)
  const linerEndY = linerY + 14;

  // 3 étiquettes posées sur le liner (avec un léger skew pour la perspective)
  const NB_ETIQ = 3;
  const linerLen = linerEndX - linerStartX;
  const etiqSpan = linerLen / (NB_ETIQ + 0.5);
  const etiqW = etiqSpan * 0.7;
  const etiqGap = etiqSpan * 0.3;
  const etiqH = linerHEpais - 12;

  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Vue B — bobine livrée (perspective)
      </figcaption>
      <svg
        viewBox={`0 0 ${VBW} ${VBH}`}
        width="100%"
        className="font-sans"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="grad-bobine" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#E5E7EB" />
            <stop offset="50%" stopColor="#F3F4F6" />
            <stop offset="100%" stopColor="#D1D5DB" />
          </linearGradient>
          <linearGradient id="grad-mandrin" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6B7280" />
            <stop offset="100%" stopColor="#9CA3AF" />
          </linearGradient>
          <pattern
            id="liner-dots-iso"
            patternUnits="userSpaceOnUse"
            width={8}
            height={8}
          >
            <circle cx={2} cy={2} r={0.6} fill={COULEUR_HACHURE} />
          </pattern>
          <marker
            id="arrow-bleu-iso"
            viewBox="0 0 10 10"
            refX={9}
            refY={5}
            markerWidth={8}
            markerHeight={8}
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={COULEUR_BLEU} />
          </marker>
          <marker
            id="arc-arrow"
            viewBox="0 0 10 10"
            refX={9}
            refY={5}
            markerWidth={7}
            markerHeight={7}
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={COULEUR_BLEU} />
          </marker>
        </defs>

        {/* ===== Bobine 3D ===== */}
        {/* Face arrière (ellipse seule, derrière) */}
        <ellipse
          cx={cxAr}
          cy={cyAr}
          rx={rxBobine}
          ry={ryBobine}
          fill={COULEUR_GRIS_CLAIR}
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.8}
        />
        {/* Côté cylindrique : 2 lignes d'enveloppe haut/bas */}
        <line
          x1={cxAv}
          y1={cyAv - ryBobine}
          x2={cxAr}
          y2={cyAr - ryBobine}
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.8}
        />
        <line
          x1={cxAv}
          y1={cyAv + ryBobine}
          x2={cxAr}
          y2={cyAr + ryBobine}
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.8}
        />
        {/* Tranche cylindrique (rectangle 4 coins) avec dégradé */}
        <path
          d={`M ${cxAv} ${cyAv - ryBobine}
              L ${cxAr} ${cyAr - ryBobine}
              L ${cxAr} ${cyAr + ryBobine}
              L ${cxAv} ${cyAv + ryBobine} Z`}
          fill="url(#grad-bobine)"
        />

        {/* Face avant (ellipse pleine) */}
        <ellipse
          cx={cxAv}
          cy={cyAv}
          rx={rxBobine}
          ry={ryBobine}
          fill="#F3F4F6"
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={1}
        />
        {/* 3 cernes concentriques (couches de matière) */}
        {[0.85, 0.65, 0.45].map((f, i) => (
          <ellipse
            key={i}
            cx={cxAv}
            cy={cyAv}
            rx={rxBobine * f}
            ry={ryBobine * f}
            fill="none"
            stroke={COULEUR_GRIS_CLAIR}
            strokeWidth={0.4}
            strokeDasharray="2 2"
          />
        ))}

        {/* Mandrin (ellipse intérieure avec dégradé sombre) */}
        <ellipse
          cx={cxAv}
          cy={cyAv}
          rx={rxMandrin}
          ry={ryMandrin}
          fill="url(#grad-mandrin)"
          stroke={COULEUR_GRIS_FONCE}
          strokeWidth={0.8}
        />
        <ellipse
          cx={cxAv}
          cy={cyAv}
          rx={rxMandrin * 0.6}
          ry={ryMandrin * 0.6}
          fill={COULEUR_MANDRIN}
          stroke="none"
        />

        {/* Cote ø mandrin (interne, petite) */}
        <text
          x={cxAv}
          y={cyAv + ryMandrin + 14}
          textAnchor="middle"
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
        >
          ø mandrin {/* eslint-disable-next-line */}
        </text>
        <text
          x={cxAv}
          y={cyAv + ryMandrin + 24}
          textAnchor="middle"
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
        >
          (renseigné dans le formulaire)
        </text>

        {/* ===== Liner sortant ===== */}
        {/* Sandwich liner + étiquettes : trapèze coloré */}
        <path
          d={`M ${linerStartX} ${linerY}
              L ${linerEndX} ${linerEndY}
              L ${linerEndX} ${linerEndY + linerHEpais}
              L ${linerStartX} ${linerY + linerHEpais} Z`}
          fill={COULEUR_LINER}
          stroke={COULEUR_HACHURE}
          strokeWidth={0.6}
        />
        <path
          d={`M ${linerStartX} ${linerY}
              L ${linerEndX} ${linerEndY}
              L ${linerEndX} ${linerEndY + linerHEpais}
              L ${linerStartX} ${linerY + linerHEpais} Z`}
          fill="url(#liner-dots-iso)"
          opacity={0.5}
        />

        {/* 3 étiquettes posées dessus, avec léger skew pour perspective */}
        {Array.from({ length: NB_ETIQ }).map((_, i) => {
          const px = linerStartX + 12 + i * (etiqW + etiqGap);
          // Légère interpolation Y pour suivre la pente
          const yProg =
            (px - linerStartX) / (linerEndX - linerStartX);
          const py = linerY + 6 + yProg * (linerEndY - linerY) - 2;
          return (
            <g
              key={i}
              transform={`translate(${px}, ${py}) skewX(-8)`}
            >
              <rect
                x={0}
                y={0}
                width={etiqW}
                height={etiqH}
                fill={COULEUR_BLEU_CLAIR}
                stroke={COULEUR_BLEU}
                strokeWidth={0.8}
              />
              <text
                x={etiqW / 2}
                y={etiqH / 2}
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

        {/* Repère START orange sur la couche externe de la bobine */}
        <g transform={`translate(${cxAv + rxBobine * 0.92}, ${cyAv - ryBobine * 0.3})`}>
          <rect
            x={-6}
            y={-6}
            width={12}
            height={12}
            fill={COULEUR_ORANGE}
            stroke="white"
            strokeWidth={0.5}
          />
          <text
            x={16}
            y={4}
            fontSize={10}
            fontWeight={700}
            fill={COULEUR_ORANGE}
          >
            START
          </text>
        </g>

        {/* Flèche enroulement (arc sur la face avant) */}
        <path
          d={`M ${cxAv - rxBobine * 0.55} ${cyAv}
              A ${rxBobine * 0.55} ${ryBobine * 0.55} 0 1 1 ${cxAv + rxBobine * 0.55} ${cyAv}`}
          fill="none"
          stroke={COULEUR_BLEU}
          strokeWidth={1}
          markerEnd="url(#arc-arrow)"
        />
        <text
          x={cxAv}
          y={cyAv - ryBobine * 0.65}
          textAnchor="middle"
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_BLEU}
        >
          {config.sens_enroulement}
        </text>

        {/* Cote ø bobine (sous la face avant) */}
        <line
          x1={cxAv - rxBobine}
          y1={cyAv + ryBobine + 22}
          x2={cxAv + rxBobine}
          y2={cyAv + ryBobine + 22}
          stroke={COULEUR_BLEU}
          strokeWidth={0.8}
        />
        <line
          x1={cxAv - rxBobine}
          y1={cyAv + ryBobine + 17}
          x2={cxAv - rxBobine}
          y2={cyAv + ryBobine + 27}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <line
          x1={cxAv + rxBobine}
          y1={cyAv + ryBobine + 17}
          x2={cxAv + rxBobine}
          y2={cyAv + ryBobine + 27}
          stroke={COULEUR_BLEU}
          strokeWidth={0.4}
        />
        <text
          x={cxAv}
          y={cyAv + ryBobine + 38}
          textAnchor="middle"
          fontSize={11}
          fontWeight={700}
          fill={COULEUR_BLEU}
        >
          ø bobine {config.diametre_bobine_mm} mm
        </text>

        {/* Sens enroulement (texte en haut-gauche) */}
        <g transform="translate(20, 30)">
          <rect
            x={-4}
            y={-12}
            width={70}
            height={20}
            rx={3}
            fill={COULEUR_BLEU_CLAIR}
            stroke={COULEUR_BLEU}
            strokeWidth={0.6}
          />
          <text
            x={31}
            y={2}
            textAnchor="middle"
            fontSize={11}
            fontWeight={700}
            fill={COULEUR_BLEU}
          >
            {config.sens_enroulement}
          </text>
        </g>

        {/* Cote liner sortant (laize liner sur la bande) */}
        <text
          x={(linerStartX + linerEndX) / 2}
          y={linerY + linerHEpais + 18}
          textAnchor="middle"
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_GRIS_FONCE}
        >
          laize liner {config.laize_liner_mm} mm
        </text>

        {/* Flèche défilement bobine vers liner (au-dessus) */}
        <line
          x1={linerStartX + 10}
          y1={linerY - 14}
          x2={linerEndX - 10}
          y2={linerEndY - 14}
          stroke={COULEUR_BLEU}
          strokeWidth={1.2}
          markerEnd="url(#arrow-bleu-iso)"
        />
        <text
          x={(linerStartX + linerEndX) / 2}
          y={linerY - 20}
          textAnchor="middle"
          fontSize={9}
          fontWeight={600}
          fill={COULEUR_BLEU}
        >
          déroulement
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

        {/* Bande liner */}
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

        {/* Cote dev étiquette (au-dessus de la première) */}
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

        {/* Cote int. dev entre 1ʳᵉ et 2ᵉ étiquette */}
        <text
          x={ox + etiqW + intervalleDevUnits / 2}
          y={oy + etiqH + 24}
          textAnchor="middle"
          fontSize={9}
          fill={COULEUR_ORANGE}
        >
          int. dev {config.intervalle_dev_reel_mm}
        </text>

        {/* Cote laize étiquette à droite */}
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

        {/* Cote laize liner à gauche (vertical) */}
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

        {/* Flèche défilement bien visible (bandeau en bas) */}
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
