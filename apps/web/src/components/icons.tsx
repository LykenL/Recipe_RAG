import type { SVGProps } from 'react'

type P = SVGProps<SVGSVGElement>

const base = (p: P) => ({
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  'aria-hidden': true,
  ...p,
})

export const ChefHat = (p: P) => (
  <svg {...base(p)}>
    <path
      d="M7.2 13.6A3.9 3.9 0 0 1 8.6 6.4a4.3 4.3 0 0 1 6.8 0 3.9 3.9 0 0 1 1.4 7.2v5.6H7.2v-5.6Z"
      fill="#fff"
    />
    <path d="M7.2 16.6h9.6" stroke="#CE4A18" strokeWidth="1.5" />
  </svg>
)

export const Sparkle = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3Z" fill="currentColor" />
  </svg>
)

export const Check = (p: P) => (
  <svg {...base(p)}>
    <path d="m5 13 4 4L19 7" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export const Search = (p: P) => (
  <svg {...base(p)}>
    <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="2.2" />
    <path d="m16 16 4 4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
  </svg>
)

export const Filter = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 6h16M7 12h10M10 18h4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
  </svg>
)

export const Dots = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="3" fill="currentColor" />
  </svg>
)

export const Plus = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
  </svg>
)

export const X = (p: P) => (
  <svg {...base(p)}>
    <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
  </svg>
)

export const Chevron = (p: P) => (
  <svg {...base(p)}>
    <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export const ArrowUp = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 19V5M6 11l6-6 6 6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export const StopIcon = (p: P) => (
  <svg {...base(p)}>
    <rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor" />
  </svg>
)

export const Clock = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.9" />
    <path d="M12 7.5V12l3 2" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
  </svg>
)

export const Protein = (p: P) => (
  <svg {...base(p)}>
    <path d="M6 4v7a6 6 0 0 0 12 0V4M9 20h6" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
  </svg>
)

export const Dessert = (p: P) => (
  <svg {...base(p)}>
    <path d="M5 13a7 7 0 0 1 14 0v5H5v-5Z" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round" />
    <path d="M12 6V3" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
  </svg>
)

export const Basket = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 8h16l-1.5 11h-13L4 8Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M9 8V6a3 3 0 0 1 6 0v2" stroke="currentColor" strokeWidth="1.8" />
  </svg>
)

export const Copy = (p: P) => (
  <svg {...base(p)}>
    <rect x="9" y="9" width="11" height="11" rx="2.4" stroke="currentColor" strokeWidth="1.9" />
    <path d="M5 15V5.5A1.5 1.5 0 0 1 6.5 4H15" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
  </svg>
)

export const Book = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v15H6.5A2.5 2.5 0 0 0 4 20.5v-15Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H19" stroke="currentColor" strokeWidth="1.8" />
  </svg>
)

export const Menu = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" />
  </svg>
)

export const Sliders = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 8h10M18 8h2M4 16h2M10 16h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <circle cx="16" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.9" />
    <circle cx="8" cy="16" r="2.2" stroke="currentColor" strokeWidth="1.9" />
  </svg>
)

export const Warn = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 4.5 21 19H3l9-14.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M12 10v4M12 17h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
)

/* ── kitchen ─────────────────────────────────────────────────────────────── */

/** Whisk — used for "the chef is working", in place of a generic sparkle. */
export const Whisk = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 3v9" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
    <path
      d="M12 12c-3 0-5 2.2-5 5.2 0 2.3 2.2 3.8 5 3.8s5-1.5 5-3.8c0-3-2-5.2-5-5.2Z"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinejoin="round"
    />
    <path d="M12 12c-1.6 1.4-2.4 3-2.4 5M12 12c1.6 1.4 2.4 3 2.4 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
  </svg>
)

/** Frying pan — used for the "Sear / cook" style steps. */
export const Pan = (p: P) => (
  <svg {...base(p)}>
    <path d="M4 8h11a5 5 0 0 1 0 10H4V8Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M15 13h5.5" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
  </svg>
)

export const Flame = (p: P) => (
  <svg {...base(p)}>
    <path
      d="M12 3s4.5 4 4.5 8a4.5 4.5 0 1 1-9 0c0-1.6.7-2.9 1.6-4 .2 1.3 1 2 1.9 2 0-2 .3-4.2 1-6Z"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinejoin="round"
    />
  </svg>
)

/** Herb sprig — decorative accent for empty states. */
export const Sprig = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 21V6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    <path d="M12 12c0-2.5 1.8-4.5 4.5-4.5M12 12c0-2.5-1.8-4.5-4.5-4.5M12 16c0-2.5 1.8-4.5 4.5-4.5M12 16c0-2.5-1.8-4.5-4.5-4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
)
