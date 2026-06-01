/**
 * Types for the global paginated search.
 *
 * A flat "search index" — one record per brand, store, material, and filament —
 * is produced two ways that share this shape:
 *   - Cloud: generated at data-build time into /api/v1/search-index.json (served by the CDN).
 *   - Local: built on the fly from the /data filesystem by /api/search-index.
 *
 * The whole index is loaded once and searched + paginated client-side
 * (see $lib/services/searchIndex.ts).
 */

export type SearchEntityType = 'brand' | 'store' | 'material' | 'filament';

export interface SearchRecord {
	type: SearchEntityType;
	/** Primary display name. brand/store/filament: the name; material: the material string ("PLA"). */
	name: string;
	/** App route this card links to (mode-correct, leading slash). */
	href: string;
	/** Brand context: for material & filament the owning brand; for brand itself; absent for store. */
	brandName?: string;
	/** Slug used to link/resolve the brand (parent brand for material/filament). */
	brandSlug?: string;
	/** Logo filename — brand/store only (cloud: logo_slug; local: raw logo.<ext> filename). */
	logo?: string;
	/** Material context (UPPERCASE materialType, e.g. "PLA") — materials & filaments. */
	materialType?: string;
	/** Extra free-text the matcher tokenizes (origin, website, etc.). */
	keywords?: string;
	/** Change-tree key, used to layer local edits and to dedupe: e.g. brands/acme/materials/PLA/filaments/foo. */
	path: string;
}

/** Envelope shape emitted by both producers. */
export interface SearchIndexFile {
	version?: string;
	generated_at?: string;
	count: number;
	records: SearchRecord[];
}

/** Result of a paginated search query. */
export interface SearchResult {
	results: SearchRecord[];
	/** Total matches across all pages. */
	total: number;
	/** 1-based current page (clamped to [1, pageCount]). */
	page: number;
	/** Total number of pages (at least 1). */
	pageCount: number;
}
