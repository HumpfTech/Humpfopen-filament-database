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

// Cleanup old jobs (older than 5 minutes)
setInterval(() => {
	const now = Date.now();
	for (const [jobId, job] of activeJobs.entries()) {
		if (job.endTime && now - job.endTime > 5 * 60 * 1000) {
			activeJobs.delete(jobId);
		}
	}
}, 60 * 1000); // Run every minute
