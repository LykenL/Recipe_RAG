/**
 * Dietary restriction checking.
 *
 * IMPORTANT — this is a *check*, not a filter. The backend passes the user's
 * restrictions to the model as instructions but does not exclude anything from
 * retrieval, so nothing here may claim a recipe was "removed" or "excluded".
 * What this does is look at the passages that were actually retrieved and say
 * which ones look like they conflict.
 *
 * False positives are the safe direction for an allergy, but they are still
 * annoying, so the matching is word-boundary based and deliberately avoids the
 * classic traps: "nutmeg" and "coconut" are not tree nuts, "butternut" is a
 * squash, "buttermilk" is dairy but contains "butter" only as a prefix.
 */

export interface RestrictionRule {
  /** label as shown in the sidebar */
  label: string
  /** single words / phrases that indicate a conflict */
  terms: string[]
}

const RULES: RestrictionRule[] = [
  {
    label: 'Nut allergy',
    terms: [
      'nut', 'nuts', 'peanut', 'peanuts', 'almond', 'almonds', 'cashew', 'cashews',
      'walnut', 'walnuts', 'pecan', 'pecans', 'pistachio', 'pistachios',
      'hazelnut', 'hazelnuts', 'macadamia', 'pine nut', 'pine nuts',
      'praline', 'marzipan', 'nutella',
    ],
  },
  {
    label: 'Vegetarian',
    terms: [
      'chicken', 'beef', 'pork', 'lamb', 'veal', 'turkey', 'duck', 'bacon', 'ham',
      'sausage', 'chorizo', 'pancetta', 'prosciutto', 'salami', 'mince', 'steak',
      'fish', 'salmon', 'tuna', 'cod', 'prawn', 'prawns', 'shrimp', 'anchovy',
      'anchovies', 'oyster', 'oysters', 'clam', 'clams', 'squid', 'mussel',
      'gelatin', 'lard', 'brisket', 'meatball', 'meatballs',
    ],
  },
  {
    label: 'Gluten-free',
    terms: [
      'wheat', 'flour', 'bread', 'breadcrumbs', 'breadcrumb', 'pasta', 'spaghetti',
      'noodle', 'noodles', 'macaroni', 'couscous', 'barley', 'rye', 'semolina',
      'spelt', 'puff pastry', 'filo', 'phyllo', 'cracker', 'crackers', 'beer',
      'soy sauce', 'batter', 'shortcrust',
    ],
  },
  {
    label: 'Dairy-free',
    terms: [
      'milk', 'butter', 'buttermilk', 'cream', 'creme', 'crème', 'cheese', 'parmesan',
      'mozzarella', 'cheddar', 'yoghurt', 'yogurt', 'ghee', 'custard', 'mascarpone',
    ],
  },
]

export interface Conflict {
  restriction: string
  /** the terms that matched */
  terms: string[]
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Which of the user's restrictions this text appears to violate.
 *
 * Returns one entry per restriction (never per term) so the UI can render a
 * single clear flag instead of a wall of matches.
 */
export function findConflicts(text: string, restrictions: string[]): Conflict[] {
  if (!restrictions.length || !text) return []
  const haystack = ` ${text.toLowerCase().replace(/[^a-z0-9]+/g, ' ')} `

  const found: Conflict[] = []
  for (const rule of RULES) {
    if (!restrictions.includes(rule.label)) continue
    const hits = rule.terms.filter((t) => {
      // Whole-word match, with an optional plural "s" at the end so that
      // "pine nuts" matches the term "pine nut". The trailing boundary is what
      // keeps "nut" out of "nutmeg" and "butternut".
      const pattern = `(^|[^a-z])${escapeRe(t).replace(/\s+/g, '[^a-z]+')}s?([^a-z]|$)`
      return new RegExp(pattern).test(haystack)
    })
    if (hits.length > 0) found.push({ restriction: rule.label, terms: [...new Set(hits)] })
  }
  return found
}

/** The text a source is judged on: title plus whatever passage we have. */
export function sourceText(title: string, snippet?: string, full?: string): string {
  return [title, full || snippet || ''].join(' ')
}
