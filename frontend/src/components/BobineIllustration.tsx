"use client";

/**
 * Illustration vectorielle d'une bobine d'étiquettes flexographiques —
 * prototype SE1 (face extérieur, A à 0°).
 *
 * Style : isométrique 3/4 légère, semi-réaliste, lisible en petite taille
 * comme en grande. Vocabulaire métier ICE :
 *   - mandrin carton kraft (cercle interne avec teinte beige)
 *   - bobine cylindrique avec couches enroulées suggérées
 *   - liner siliconé (backing) en bande qui se déroule
 *   - 4 étiquettes alignées dont la dernière porte le A
 *   - repère START orange tangent à la couche externe
 *   - flèche déroulement courbée au-dessus du liner
 *
 * Couleurs cohérentes avec le reste du schéma BAT (#0C447C bleu, #993C1D
 * orange). Mandrin kraft pour rappeler le matériau réel.
 */
export function BobineIllustration({
  width = 320,
  height = 220,
}: {
  width?: number;
  height?: number;
}) {
  return (
    <svg
      viewBox="0 0 320 220"
      width={width}
      height={height}
      className="font-sans"
      aria-label="Bobine SE1 — face extérieur, A à 0°"
    >
      <defs>
        {/* Dégradé radial bobine : couches enroulées + relief volumétrique */}
        <radialGradient id="bobine-radial" cx="42%" cy="38%" r="62%">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="55%" stopColor="#F3F4F6" />
          <stop offset="85%" stopColor="#D1D5DB" />
          <stop offset="100%" stopColor="#9CA3AF" />
        </radialGradient>
        {/* Dégradé mandrin carton kraft */}
        <radialGradient id="mandrin-kraft" cx="40%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#D4A574" />
          <stop offset="60%" stopColor="#B5803F" />
          <stop offset="100%" stopColor="#7A5A2E" />
        </radialGradient>
        {/* Pattern points liner siliconé */}
        <pattern
          id="liner-dots-bob"
          patternUnits="userSpaceOnUse"
          width={8}
          height={8}
        >
          <circle cx={2} cy={2} r={0.7} fill="#C8C6BC" />
        </pattern>
        {/* Marker flèche bleu */}
        <marker
          id="arrow-bob"
          viewBox="0 0 10 10"
          refX={9}
          refY={5}
          markerWidth={9}
          markerHeight={9}
          orient="auto"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#0C447C" />
        </marker>
        {/* Ombre douce sous la bobine */}
        <filter id="bobine-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="3" />
          <feOffset dx="0" dy="4" />
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.3" />
          </feComponentTransfer>
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Soubassement (ombre portée sous la bobine) */}
      <ellipse cx={80} cy={185} rx={62} ry={6} fill="#000" opacity={0.12} />

      {/* === BOBINE === */}
      <g filter="url(#bobine-shadow)">
        {/* Disque extérieur (face avant) */}
        <circle
          cx={80}
          cy={110}
          r={68}
          fill="url(#bobine-radial)"
          stroke="#4B5563"
          strokeWidth={1.2}
        />

        {/* Couches enroulées : cercles concentriques décroissants */}
        {[0.92, 0.82, 0.7, 0.58, 0.45, 0.36].map((ratio, i) => (
          <circle
            key={i}
            cx={80}
            cy={110}
            r={68 * ratio}
            fill="none"
            stroke="#9CA3AF"
            strokeWidth={0.4}
            strokeDasharray={i === 0 ? "none" : "1.5 1.8"}
            opacity={0.55}
          />
        ))}

        {/* Bandeau de couches plus marqué près du bord (couches récentes) */}
        <circle
          cx={80}
          cy={110}
          r={66}
          fill="none"
          stroke="#6B7280"
          strokeWidth={0.6}
          opacity={0.4}
        />

        {/* Reflet doux sur la face avant (rendu volumétrique) */}
        <ellipse
          cx={62}
          cy={88}
          rx={24}
          ry={14}
          fill="white"
          opacity={0.4}
        />

        {/* Mandrin carton kraft */}
        <circle
          cx={80}
          cy={110}
          r={20}
          fill="url(#mandrin-kraft)"
          stroke="#5B3F1F"
          strokeWidth={0.8}
        />
        {/* Anneau ombré intérieur du mandrin */}
        <circle
          cx={80}
          cy={110}
          r={12}
          fill="#3E2914"
          stroke="#1F1408"
          strokeWidth={0.5}
        />
        {/* Petit reflet du trou mandrin */}
        <ellipse
          cx={76}
          cy={106}
          rx={3}
          ry={2}
          fill="#5B3F1F"
          opacity={0.7}
        />
      </g>

      {/* Repère START orange tangent à la couche externe (en haut) */}
      <g transform="translate(118 56)">
        <rect
          x={-4}
          y={-4}
          width={8}
          height={8}
          fill="#993C1D"
          stroke="white"
          strokeWidth={0.5}
        />
        <text
          x={9}
          y={3}
          fontSize={9}
          fontWeight={700}
          fill="#993C1D"
        >
          START
        </text>
      </g>

      {/* === LINER SORTANT === */}
      {/* Le liner part du sommet de la bobine vers la droite, légère pente
          descendante pour évoquer la sortie tangente. */}
      <g>
        {/* Bande liner principale */}
        <path
          d="M 138 78
             Q 175 78 200 80
             L 305 88
             L 305 124
             L 200 116
             Q 175 114 138 114
             Z"
          fill="#FAF7EE"
          stroke="#C8C6BC"
          strokeWidth={0.7}
        />
        {/* Pattern points sur le liner */}
        <path
          d="M 138 78
             Q 175 78 200 80
             L 305 88
             L 305 124
             L 200 116
             Q 175 114 138 114
             Z"
          fill="url(#liner-dots-bob)"
          opacity={0.5}
        />
      </g>

      {/* === ÉTIQUETTES sur le liner === */}
      {/* 4 étiquettes paysage alignées sur la bande. La dernière (la plus
          éloignée de la bobine, à droite) porte le A. */}
      {[
        { x: 158, y: 84, w: 32, h: 22, withA: false },
        { x: 196, y: 86, w: 32, h: 22, withA: false },
        { x: 234, y: 88, w: 32, h: 22, withA: false },
        { x: 272, y: 90, w: 32, h: 22, withA: true },
      ].map((etiq, i) => (
        <g key={i}>
          <rect
            x={etiq.x}
            y={etiq.y}
            width={etiq.w}
            height={etiq.h}
            fill="#DCE7F3"
            stroke="#0C447C"
            strokeWidth={0.8}
            rx={1}
          />
          {etiq.withA && (
            <text
              x={etiq.x + etiq.w / 2}
              y={etiq.y + etiq.h / 2}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={14}
              fontWeight={700}
              fill="#0C447C"
            >
              A
            </text>
          )}
        </g>
      ))}

      {/* === Flèche déroulement courbée au-dessus du liner === */}
      <g>
        <path
          d="M 150 65 Q 220 50 295 70"
          fill="none"
          stroke="#0C447C"
          strokeWidth={1.5}
          markerEnd="url(#arrow-bob)"
        />
        <text
          x={220}
          y={48}
          textAnchor="middle"
          fontSize={10}
          fontWeight={700}
          fill="#0C447C"
        >
          déroulement
        </text>
      </g>

      {/* === Badge SE1 + label === */}
      <g transform="translate(10 12)">
        <rect
          x={0}
          y={0}
          width={120}
          height={26}
          rx={4}
          fill="#DCE7F3"
          stroke="#0C447C"
          strokeWidth={0.6}
        />
        <text
          x={60}
          y={11}
          textAnchor="middle"
          fontSize={11}
          fontWeight={700}
          fill="#0C447C"
        >
          SE1
        </text>
        <text x={60} y={21} textAnchor="middle" fontSize={8} fill="#0C447C">
          0° extérieur
        </text>
      </g>

      {/* === Cote ø bobine sous la bobine === */}
      <g>
        <line
          x1={12}
          y1={195}
          x2={148}
          y2={195}
          stroke="#0C447C"
          strokeWidth={0.7}
        />
        <line x1={12} y1={191} x2={12} y2={199} stroke="#0C447C" strokeWidth={0.4} />
        <line x1={148} y1={191} x2={148} y2={199} stroke="#0C447C" strokeWidth={0.4} />
        <text
          x={80}
          y={210}
          textAnchor="middle"
          fontSize={9}
          fontWeight={600}
          fill="#0C447C"
        >
          ø bobine
        </text>
      </g>

      {/* === Vocabulaire métier (annotations légères) === */}
      <text x={180} y={140} fontSize={8} fill="#6B7280" fontStyle="italic">
        liner siliconé (backing)
      </text>
      <text x={80} y={148} textAnchor="middle" fontSize={7} fill="#5B3F1F" fontStyle="italic">
        mandrin carton
      </text>
    </svg>
  );
}
