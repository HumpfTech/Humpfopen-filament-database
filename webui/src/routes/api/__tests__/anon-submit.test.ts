/**
 * Tests for the /api/anon/submit endpoint (SimplyPrint-authenticated bot submit).
 *
 * Covers the routing layer's branches:
 *  - Feature-flag rejection
 *  - SimplyPrint auth requirement
 *  - Rate limiting
 *  - JSON parsing + empty changes
 *  - Validation success / error / invalid response paths
 *  - PR creation success / failure
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mocks = vi.hoisted(() => ({
	isAnonBotEnabled: vi.fn(() => true),
	createAnonPR: vi.fn(),
	runCloudValidation: vi.fn(),
	sendWebhook: vi.fn(),
	trackSubmission: vi.fn(),
	getSimplyPrintToken: vi.fn(() => 'fake-token'),
	getSimplyPrintUser: vi.fn(async () => ({ id: 1, email: 'u@example.com' })),
	checkRateLimit: vi.fn(() => ({ allowed: true }))
}));

vi.mock('$lib/server/anonBot', () => ({
	isAnonBotEnabled: mocks.isAnonBotEnabled,
	createAnonPR: mocks.createAnonPR
}));
vi.mock('$lib/server/cloudValidator', () => ({
	runCloudValidation: mocks.runCloudValidation
}));
vi.mock('$lib/server/webhooks', () => ({ sendWebhook: mocks.sendWebhook }));
vi.mock('$lib/server/submissionStore', () => ({ trackSubmission: mocks.trackSubmission }));
vi.mock('$lib/server/auth', () => ({
	getSimplyPrintToken: mocks.getSimplyPrintToken,
	getSimplyPrintUser: mocks.getSimplyPrintUser
}));
vi.mock('$lib/server/rateLimit', () => ({ checkRateLimit: mocks.checkRateLimit }));

vi.mock('@sveltejs/kit', () => ({
	json: (data: any, init?: { status?: number; headers?: any }) => ({
		status: init?.status ?? 200,
		headers: init?.headers,
		body: data,
		json: async () => data
	})
}));

import { POST } from '../anon/submit/+server';

function makeEvent(body: any, opts: { ip?: string } = {}): any {
	return {
		request: { json: async () => body },
		cookies: { get: () => 'cookie-value' },
		getClientAddress: () => opts.ip ?? '127.0.0.1'
	};
}

describe('POST /api/anon/submit', () => {
	beforeEach(() => {
		for (const fn of Object.values(mocks)) (fn as any).mockReset?.();
		mocks.isAnonBotEnabled.mockReturnValue(true);
		mocks.getSimplyPrintToken.mockReturnValue('fake-token');
		mocks.getSimplyPrintUser.mockResolvedValue({ id: 1, email: 'u@example.com' });
		mocks.checkRateLimit.mockReturnValue({ allowed: true });
		mocks.runCloudValidation.mockImplementation(async (job: any) => {
			job.status = 'complete';
			job.result = { is_valid: true };
		});
		mocks.createAnonPR.mockResolvedValue({
			success: true,
			prNumber: 42,
			prUrl: 'https://github.com/foo/bar/pull/42'
		});
	});

	it('returns 404 when the bot feature flag is off', async () => {
		mocks.isAnonBotEnabled.mockReturnValue(false);
		const res: any = await POST(makeEvent({ changes: [] }));
		expect(res.status).toBe(404);
		expect(res.body.error).toMatch(/not enabled/i);
	});

	it('returns 401 when SimplyPrint token is missing', async () => {
		mocks.getSimplyPrintToken.mockReturnValue(undefined);
		const res: any = await POST(makeEvent({ changes: [] }));
		expect(res.status).toBe(401);
		expect(res.body.error).toMatch(/authentication required/i);
	});

	it('returns 401 when SimplyPrint user lookup throws', async () => {
		mocks.getSimplyPrintUser.mockRejectedValue(new Error('expired'));
		const res: any = await POST(makeEvent({ changes: [{ x: 1 }] }));
		expect(res.status).toBe(401);
		expect(res.body.error).toMatch(/session expired/i);
	});

	it('returns 429 with Retry-After header when rate limit exceeded', async () => {
		mocks.checkRateLimit.mockReturnValue({ allowed: false, retryAfterMs: 60000 });
		const res: any = await POST(makeEvent({ changes: [] }));
		expect(res.status).toBe(429);
		expect(res.headers['Retry-After']).toBe('60');
	});

	it('returns 400 when body JSON cannot be parsed', async () => {
		const res: any = await POST({
			request: { json: async () => { throw new Error('bad'); } },
			cookies: { get: () => 'x' },
			getClientAddress: () => '127.0.0.1'
		} as any);
		expect(res.status).toBe(400);
		expect(res.body.error).toMatch(/Invalid JSON/);
	});

	it('returns 400 when changes array is empty', async () => {
		const res: any = await POST(makeEvent({ changes: [] }));
		expect(res.status).toBe(400);
		expect(res.body.error).toMatch(/No changes/);
	});

	it('returns 400 when validation job errors', async () => {
		mocks.runCloudValidation.mockImplementation(async (job: any) => {
			job.status = 'error';
			job.events.push({ type: 'error', message: 'validator broke' });
		});
		const res: any = await POST(makeEvent({ changes: [{ a: 1 }] }));
		expect(res.status).toBe(400);
		expect(res.body.error).toBe('validator broke');
	});

	it('returns 422 with validation result when changes are invalid', async () => {
		mocks.runCloudValidation.mockImplementation(async (job: any) => {
			job.status = 'complete';
			job.result = { is_valid: false, errors: ['bad field'] };
		});
		const res: any = await POST(makeEvent({ changes: [{ a: 1 }] }));
		expect(res.status).toBe(422);
		expect(res.body.error).toBe('Validation errors found');
		expect(res.body.validation.is_valid).toBe(false);
	});

	it('returns 500 when PR creation reports failure', async () => {
		mocks.createAnonPR.mockResolvedValue({ success: false, error: 'github 502' });
		const res: any = await POST(makeEvent({ changes: [{ a: 1 }] }));
		expect(res.status).toBe(500);
		expect(res.body.error).toBe('github 502');
	});

	it('returns 500 when PR creation throws', async () => {
		mocks.createAnonPR.mockRejectedValue(new Error('boom'));
		const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
		const res: any = await POST(makeEvent({ changes: [{ a: 1 }] }));
		expect(res.status).toBe(500);
		expect(res.body.error).toBe('boom');
		errSpy.mockRestore();
	});

	it('happy path: tracks submission, sends webhook, returns uuid + PR info', async () => {
		const res: any = await POST(
			makeEvent({
				changes: [{ entity: { path: 'brands/acme' }, operation: 'update' }],
				images: {},
				title: 'Add Acme',
				description: 'desc'
			})
		);

		expect(res.status).toBe(200);
		expect(res.body.success).toBe(true);
		expect(res.body.uuid).toMatch(/^[0-9a-f]{8}-/);
		expect(res.body.prNumber).toBe(42);
		expect(res.body.prUrl).toContain('/pull/42');

		expect(mocks.trackSubmission).toHaveBeenCalledTimes(1);
		expect(mocks.trackSubmission.mock.calls[0][0]).toBe(res.body.uuid);
		expect(mocks.trackSubmission.mock.calls[0][1]).toBe(42);
		expect(mocks.trackSubmission.mock.calls[0][4]).toBe('u@example.com');

		expect(mocks.sendWebhook).toHaveBeenCalledTimes(1);
		expect(mocks.sendWebhook.mock.calls[0][0].event).toBe('submitted');
	});
});
