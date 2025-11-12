// IndexedDB wrapper for persistent job storage
// Ensures job data survives browser restarts

class JobStorage {
    constructor() {
        this.dbName = 'SimplePageSaverDB';
        this.dbVersion = 1;
        this.db = null;
    }

    /**
     * Initialize the database
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => {
                console.error('[JobStorage] Failed to open database:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('[JobStorage] Database opened successfully');
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Create jobs object store if it doesn't exist
                if (!db.objectStoreNames.contains('jobs')) {
                    const objectStore = db.createObjectStore('jobs', { keyPath: 'id' });

                    // Create indexes for efficient querying
                    objectStore.createIndex('status', 'status', { unique: false });
                    objectStore.createIndex('type', 'type', { unique: false });
                    objectStore.createIndex('created_at', 'created_at', { unique: false });

                    console.log('[JobStorage] Jobs object store created');
                }
            };
        });
    }

    /**
     * Ensure database is initialized
     */
    async ensureInit() {
        if (!this.db) {
            await this.init();
        }
    }

    /**
     * Save a job to IndexedDB
     * @param {object} job - Job object to save
     */
    async saveJob(job) {
        await this.ensureInit();

        // Normalize job object - ensure it has 'id' field (IndexedDB key path)
        // Backend returns 'job_id', so we need to normalize
        const normalizedJob = {
            ...job,
            id: job.id || job.job_id  // Use 'id' if present, otherwise use 'job_id'
        };

        // Ensure we have an id
        if (!normalizedJob.id) {
            console.error('[JobStorage] Job object missing both id and job_id fields:', job);
            throw new Error('Job object must have either id or job_id field');
        }

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['jobs'], 'readwrite');
            const objectStore = transaction.objectStore('jobs');

            const request = objectStore.put(normalizedJob);

            request.onsuccess = () => {
                console.log(`[JobStorage] Job saved: ${normalizedJob.id}`);
                resolve();
            };

            request.onerror = () => {
                console.error(`[JobStorage] Failed to save job ${normalizedJob.id}:`, request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Get a job by ID
     * @param {string} jobId - Job ID
     */
    async getJob(jobId) {
        await this.ensureInit();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['jobs'], 'readonly');
            const objectStore = transaction.objectStore('jobs');

            const request = objectStore.get(jobId);

            request.onsuccess = () => {
                resolve(request.result || null);
            };

            request.onerror = () => {
                console.error(`[JobStorage] Failed to get job ${jobId}:`, request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Get all jobs
     */
    async getAllJobs() {
        await this.ensureInit();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['jobs'], 'readonly');
            const objectStore = transaction.objectStore('jobs');

            const request = objectStore.getAll();

            request.onsuccess = () => {
                resolve(request.result || []);
            };

            request.onerror = () => {
                console.error('[JobStorage] Failed to get all jobs:', request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Get jobs by status
     * @param {string} status - Job status (pending, processing, paused, completed, failed)
     */
    async getJobsByStatus(status) {
        await this.ensureInit();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['jobs'], 'readonly');
            const objectStore = transaction.objectStore('jobs');
            const index = objectStore.index('status');

            const request = index.getAll(status);

            request.onsuccess = () => {
                resolve(request.result || []);
            };

            request.onerror = () => {
                console.error(`[JobStorage] Failed to get jobs with status ${status}:`, request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Update job status
     * @param {string} jobId - Job ID
     * @param {string} newStatus - New status
     */
    async updateJobStatus(jobId, newStatus) {
        const job = await this.getJob(jobId);
        if (!job) {
            throw new Error(`Job ${jobId} not found`);
        }

        job.status = newStatus;
        job.updated_at = new Date().toISOString();

        if (newStatus === 'paused') {
            job.paused_at = new Date().toISOString();
        } else if (newStatus === 'processing' && job.paused_at) {
            job.resumed_at = new Date().toISOString();
        }

        await this.saveJob(job);
    }

    /**
     * Update job progress
     * @param {string} jobId - Job ID
     * @param {object} progress - Progress data
     */
    async updateJobProgress(jobId, progress) {
        const job = await this.getJob(jobId);
        if (!job) {
            throw new Error(`Job ${jobId} not found`);
        }

        job.progress = progress;
        job.updated_at = new Date().toISOString();

        await this.saveJob(job);
    }

    /**
     * Delete a job
     * @param {string} jobId - Job ID
     */
    async deleteJob(jobId) {
        await this.ensureInit();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['jobs'], 'readwrite');
            const objectStore = transaction.objectStore('jobs');

            const request = objectStore.delete(jobId);

            request.onsuccess = () => {
                console.log(`[JobStorage] Job deleted: ${jobId}`);
                resolve();
            };

            request.onerror = () => {
                console.error(`[JobStorage] Failed to delete job ${jobId}:`, request.error);
                reject(request.error);
            };
        });
    }

    /**
     * Delete all completed jobs
     */
    async deleteCompletedJobs() {
        const completedJobs = await this.getJobsByStatus('completed');
        const failedJobs = await this.getJobsByStatus('failed');

        const deletePromises = [...completedJobs, ...failedJobs].map(job =>
            this.deleteJob(job.id)
        );

        await Promise.all(deletePromises);
        console.log(`[JobStorage] Deleted ${deletePromises.length} completed/failed jobs`);
    }

    /**
     * Delete old jobs (older than specified days)
     * @param {number} days - Number of days
     */
    async deleteOldJobs(days = 7) {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);

        const allJobs = await this.getAllJobs();
        const oldJobs = allJobs.filter(job => {
            const createdDate = new Date(job.created_at);
            return createdDate < cutoffDate;
        });

        const deletePromises = oldJobs.map(job => this.deleteJob(job.id));

        await Promise.all(deletePromises);
        console.log(`[JobStorage] Deleted ${oldJobs.length} jobs older than ${days} days`);
    }

    /**
     * Get active jobs (pending, processing, or paused)
     */
    async getActiveJobs() {
        const pending = await this.getJobsByStatus('pending');
        const processing = await this.getJobsByStatus('processing');
        const paused = await this.getJobsByStatus('paused');

        return [...pending, ...processing, ...paused];
    }

    /**
     * Clear all jobs
     */
    async clearAll() {
        await this.ensureInit();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['jobs'], 'readwrite');
            const objectStore = transaction.objectStore('jobs');

            const request = objectStore.clear();

            request.onsuccess = () => {
                console.log('[JobStorage] All jobs cleared');
                resolve();
            };

            request.onerror = () => {
                console.error('[JobStorage] Failed to clear jobs:', request.error);
                reject(request.error);
            };
        });
    }
}

// Create singleton instance
const jobStorage = new JobStorage();

// Export for use in background.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JobStorage;
}
