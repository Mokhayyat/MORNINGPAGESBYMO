// Inline SVG pieces. Line icons follow Lucide's 24px grid (ISC licence); the BREEZE mark and the
// garment wireframe are the ones on thermalabs.io.

const line = (body, stroke = 'currentColor', w = 2.2) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;

export const ICONS = {
  flask: line('<path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2"/><path d="M6.453 15h11.094"/><path d="M8.5 2h7"/>', '#fff'),
  snowflake: line('<path d="m10 20-1.25-2.5L6 18"/><path d="M10 4 8.75 6.5 6 6"/><path d="m14 20 1.25-2.5L18 18"/><path d="m14 4 1.25 2.5L18 6"/><path d="m17 21-3-6h-4"/><path d="m17 3-3 6 1.5 3"/><path d="M2 12h6.5L10 9"/><path d="m20 10-1.5 2 1.5 2"/><path d="M22 12h-6.5L14 15"/><path d="m4 10 1.5 2L4 14"/><path d="m7 21 3-6-1.5-3"/><path d="m7 3 3 6h4"/>', '#00E0FF'),
  // globe with an animatable meridian (class "mer")
  globe: line('<circle cx="12" cy="12" r="10"/><ellipse class="mer" cx="12" cy="12" rx="4.6" ry="10"/><path d="M2 12h20"/><path d="M4.2 7h15.6M4.2 17h15.6" stroke-width="1.6"/>', '#fff'),
  arrow: line('<path d="M7 7h10v10"/><path d="M7 17 17 7"/>', '#00E0FF', 2.6),
  check: line('<path d="M20 6 9 17l-5-5"/>', '#fff', 3),
  comment: line('<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>', '#00E0FF', 2.2),
  warn: '<svg viewBox="0 0 24 24"><path d="M10.27 3.5a2 2 0 0 1 3.46 0l8.66 15a2 2 0 0 1-1.73 3H3.34a2 2 0 0 1-1.73-3z" fill="#fff"/><path d="M12 9v4.6" stroke="#F0453A" stroke-width="2.6" stroke-linecap="round"/><circle cx="12" cy="17.4" r="1.5" fill="#F0453A"/></svg>',
  heart: '<svg viewBox="0 0 24 24"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" fill="#00E0FF" stroke="#BFF8FF" stroke-width="0.8"/></svg>',
  silhouette: '<svg viewBox="0 0 96 96"><circle cx="48" cy="34" r="19" fill="#4a4f58"/><path d="M8 100c0-24 18-40 40-40s40 16 40 40z" fill="#4a4f58"/></svg>',
  mark: (color = '#fff') => `<svg viewBox="0 0 512 512"><g transform="translate(79.64 81.67) scale(3.52711)"><path d="M5 60C27 79 60 74 95 26 78 65 39 82 9 68Z" fill="${color}"/></g></svg>`,
};

// thermalabs.io "flagship" garment wireframe (shirt + jacket), drawn on with stroke-dashoffset.
export const GARMENT = `<svg viewBox="0 0 320 400" fill="none" stroke="#00E0FF" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" filter="url(#holo-glow)">
<path d="M136 86 C146 78 174 78 184 86"/><path d="M136 86 L150 110 L160 100 L170 110 L184 86"/><path d="M160 100 L160 338"/><path d="M166 100 L166 338"/>
<path d="M134 338 C148 342 172 342 190 338"/><path d="M128 92 C136 78 148 72 160 70 C172 72 184 78 192 92"/><path d="M128 92 L106 134 C102 156 112 190 132 214"/>
<path d="M112 122 L122 116"/><path d="M208 122 L198 116"/><path d="M128 92 C124 130 124 172 132 214"/><path d="M132 214 C136 246 132 300 128 352"/>
<path d="M192 92 L214 134 C218 156 208 190 188 214"/><path d="M192 92 C196 130 196 172 188 214"/><path d="M188 214 C184 246 188 300 192 352"/>
<path d="M128 92 C104 94 80 102 62 116"/><path d="M192 92 C216 94 240 102 258 116"/><path d="M62 116 C78 122 90 130 92 142"/><path d="M258 116 C242 122 230 130 228 142"/>
<path d="M62 116 C48 164 38 240 38 316"/><path d="M38 316 L72 320"/><path d="M40 304 L70 308"/><path d="M72 320 C78 250 86 180 92 142"/><path d="M92 142 C88 212 88 292 92 352"/>
<path d="M92 352 C104 356 116 356 128 352"/><path d="M228 142 C232 212 232 292 228 352"/><path d="M192 352 C204 356 216 356 228 352"/><path d="M228 142 C234 180 242 250 246 320"/>
<path d="M246 320 L280 316"/><path d="M248 308 L278 304"/><path d="M280 316 C282 240 274 160 258 116"/><path d="M100 174 L122 172"/><path d="M96 254 L122 256"/><path d="M198 252 L226 250"/>
<path class="core" d="M142 192 C176 214 188 240 166 264 C146 286 138 304 150 328" stroke="#7FF3FF" stroke-width="5" opacity="0.9"/>
</svg>`;
