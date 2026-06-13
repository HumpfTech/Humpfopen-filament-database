/**
 * Tests for prBuilder no-op delete handling.
 *
 * A delete whose target entity has no files in the upstream repo (never
 * published, or already removed) can't be expressed as a PR. buildTreeItems
 * must treat it as a no-op (produce no tree items) and report it via
 * noopDeletes, and explainEmptyTree must turn that into an actionable message.
 */
import { describe, it, expect, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
	getRecursiveTree: vi.fn(),
	createBlob: vi.fn(async () => 'blob-sha')
}));

vi.mock('$lib/server/github', () => ({
	getRecursiveTree: mocks.getRecursiveTree,
	createBlob: mocks.createBlob
}));

import { buildTreeItems, explainEmptyTree } from '../prBuilder';

const VARIANT_PATH = 'brands/acme/materials/pla/filaments/pla+/variants/oliver_green';
const VARIANT_REPO_FILE = 'data/acme/PLA/pla+/oliver_green/variant.json';

function deleteChange() {
	return [
		{
			entity: { type: 'variant', path: VARIANT_PATH, id: 'oliver_green' },
			operation: 'delete',
			description: 'Deleted variant "Oliver Green"'
		}
	];
}

describe('buildTreeItems — delete cascade', () => {
	it('records a no-op delete when the entity is absent from the upstream tree', async () => {
		// Upstream tree has unrelated files only — nothing under the deleted dir.
		mocks.getRecursiveTree.mockResolvedValue(
			new Map([['data/other/brand.json', { sha: 's', mode: '100644', type: 'blob' }]])
		);

		const result = await buildTreeItems(
			'tok', 'fork', 'repo', 'base-tree', 'up', 'repo', deleteChange(), undefined
		);

		expect(result.treeItems).toHaveLength(0);
		expect(result.noopDeletes).toEqual([
			{ path: VARIANT_PATH, description: 'Deleted variant "Oliver Green"' }
		]);
	});

	it('emits delete tree items when the entity exists upstream', async () => {
		mocks.getRecursiveTree.mockResolvedValue(
			new Map([[VARIANT_REPO_FILE, { sha: 's', mode: '100644', type: 'blob' }]])
		);

		const result = await buildTreeItems(
			'tok', 'fork', 'repo', 'base-tree', 'up', 'repo', deleteChange(), undefined
		);

		expect(result.noopDeletes).toHaveLength(0);
		expect(result.treeItems).toEqual([{ path: VARIANT_REPO_FILE, sha: null }]);
	});
});

describe('explainEmptyTree', () => {
	it('falls back to a plain message with no skips', () => {
		expect(explainEmptyTree([], [])).toBe('No changes to submit.');
	});

	it('explains a single no-op delete using its description', () => {
		const msg = explainEmptyTree([], [{ path: VARIANT_PATH, description: 'Deleted variant "Oliver Green"' }]);
		expect(msg).toContain('Deleted variant "Oliver Green"');
		expect(msg).toMatch(/isn't in the database/);
	});

	it('explains multiple no-op deletes', () => {
		const msg = explainEmptyTree([], [
			{ path: 'a', description: 'A' },
			{ path: 'b', description: 'B' }
		]);
		expect(msg).toContain('A, B');
		expect(msg).toMatch(/aren't in the database/);
	});

	it('reports unmappable skipped paths', () => {
		const msg = explainEmptyTree(['weird/path'], []);
		expect(msg).toContain('weird/path');
		expect(msg).toMatch(/couldn't be mapped/);
	});
});
