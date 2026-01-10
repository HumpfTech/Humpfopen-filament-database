// Shared job storage for validation and sort operations

export interface Job {
	id: string;
	type: 'validation' | 'sort';
	startTime: number;
	status: 'running' | 'complete' | 'error';
	events: any[];
	process?: any;
	result?: any;
	endTime?: number;
}

// In-memory job storage
export const activeJobs = new Map<string, Job>();

// Helper functions for validation job management
export function getActiveValidationJob(): Job | null {
	for (const [jobId, job] of activeJobs.entries()) {
		if (job.type === 'validation' && job.status === 'running') {
			return job;
		}
	}
	return null;
}

export function hasActiveValidationJob(): boolean {
	return getActiveValidationJob() !== null;
}

// Cleanup old jobs (older than 5 minutes) and timeout stuck jobs
setInterval(() => {
	const now = Date.now();
	for (const [jobId, job] of activeJobs.entries()) {
		// Remove old completed/errored jobs
		if (job.endTime && now - job.endTime > 5 * 60 * 1000) {
			activeJobs.delete(jobId);
		}

		// Timeout jobs running for more than 30 minutes
		if (job.status === 'running' && now - job.startTime > 30 * 60 * 1000) {
			console.error(`Job ${jobId} timed out after 30 minutes`);
			job.status = 'error';
			job.events.push({
				type: 'error',
				message: 'Job timed out after 30 minutes'
			});
			job.endTime = now;

			// Kill the process if it exists
			if (job.process?.kill) {
				job.process.kill('SIGTERM');
			}
		}
	}
}, 60 * 1000); // Run every minute
