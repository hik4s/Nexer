type Step = Record<string, unknown>;
type Recipe = {steps: Step[]};

/** Link each recorded download to a mandatory size and SHA-256 validation.
 * The runtime resolves the *actual* output of that step, including names supplied by the site.
 * This is a byte-integrity check, not a guarantee of CSV structure or business correctness.
 */
export function validationForDownload<T extends Recipe>(recipe: T, downloadId: string): Step | undefined {
  return recipe.steps.find(step => step.action === 'validate_file' && step.source_download === downloadId);
}

export function ensureDownloadValidations<T extends Recipe>(recipe: T): T {
  const known = new Set(recipe.steps.map(step => step.id));
  const output: Step[] = [];
  let changed = false;
  for (const step of recipe.steps) {
    output.push(step);
    if (step.action !== 'download' || validationForDownload(recipe, String(step.id))) continue;
    const base = `file_check_${String(step.id)}`;
    let id = base, suffix = 1;
    while (known.has(id)) id = `${base}_${suffix++}`;
    known.add(id);
    output.push({id, action: 'validate_file', source_download: step.id, min_size: 1});
    changed = true;
  }
  return changed ? {...recipe, steps: output} : recipe;
}
