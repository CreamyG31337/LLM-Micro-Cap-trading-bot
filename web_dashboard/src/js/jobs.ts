/**
 * Jobs Scheduler Dashboard
 * Handles status updates, job list rendering, and job actions
 */

// Type definitions
interface Job {
    id: string;
    actual_job_id?: string;
    name?: string;
    next_run?: string | null;
    trigger?: string;
    status?: 'running' | 'error' | 'idle' | 'paused';
    parameters?: Record<string, string>;
    recent_logs?: LogEntry[];
    is_running?: boolean;
    is_paused?: boolean;
    last_error?: string;
    running_since?: string;
}

interface LogEntry {
    timestamp: string;
    level?: string;
    message: string;
    success?: boolean;
    duration_ms?: number;
}

interface JobsStatusResponse {
    scheduler_running: boolean;
    jobs: Job[];
    error?: string;
}

interface JobsApiResponse {
    success?: boolean;
    error?: string;
    message?: string;
}

interface JobActionRequest {
    job_id: string;
    parameters?: Record<string, any>;
}

interface DOMElements {
    statusContainer: HTMLElement | null;
    errorContainer: HTMLElement | null;
    runningContainer: HTMLElement | null;
    infoText: HTMLElement | null;
    startBtn: HTMLElement | null;
    refreshBtn: HTMLElement | null;
    jobsList: HTMLElement | null;
    jobsLoading: HTMLElement | null;
    noJobs: HTMLElement | null;
    errorMsg: HTMLElement | null;
    errorText: HTMLElement | null;
    autoRefreshCheckbox: HTMLInputElement | null;
}

// State
let isSchedulerRunning = false;
let jobs: Job[] = [];
let refreshInterval: ReturnType<typeof setInterval> | null = null;
let autoRefresh = true;

// DOM Elements
const elements: DOMElements = {
    statusContainer: document.getElementById('scheduler-status-container'),
    errorContainer: document.getElementById('scheduler-error'),
    runningContainer: document.getElementById('scheduler-running'),
    infoText: document.getElementById('scheduler-info'),
    startBtn: document.getElementById('start-scheduler-btn'),
    refreshBtn: document.getElementById('refresh-status-btn'),
    jobsList: document.getElementById('jobs-list'),
    jobsLoading: document.getElementById('loading'),
    noJobs: document.getElementById('no-jobs'),
    errorMsg: document.getElementById('error-message'),
    errorText: document.getElementById('error-text'),
    autoRefreshCheckbox: document.getElementById('auto-refresh') as HTMLInputElement | null
};

// Initialize
document.addEventListener('DOMContentLoaded', (): void => {
    fetchStatus();
    startAutoRefresh();

    // Event Listeners
    if (elements.startBtn) {
        elements.startBtn.addEventListener('click', startScheduler);
    }
    if (elements.refreshBtn) {
        elements.refreshBtn.addEventListener('click', fetchStatus);
    }
    if (elements.autoRefreshCheckbox) {
        elements.autoRefreshCheckbox.addEventListener('change', (e: Event): void => {
            const target = e.target as HTMLInputElement;
            autoRefresh = target.checked;
            if (autoRefresh) {
                startAutoRefresh();
            } else {
                stopAutoRefresh();
            }
        });
    }
});

function startAutoRefresh(): void {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(() => {
        if (autoRefresh) {
            fetchStatus();
        }
    }, 5000);
}

function stopAutoRefresh(): void {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Fetch Status
async function fetchStatus(): Promise<void> {
    try {
        const response = await fetch('/api/jobs/status');
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        const data: JobsStatusResponse = await response.json();

        updateStatusUI(data.scheduler_running);
        renderJobs(data.jobs);
    } catch (error) {
        console.error('Error fetching status:', error);
        showError('Failed to fetch scheduler status');
    }
}

// Update Status UI
function updateStatusUI(running: boolean): void {
    isSchedulerRunning = running;
    if (running) {
        if (elements.errorContainer) {
            elements.errorContainer.classList.add('hidden');
        }
        if (elements.runningContainer) {
            elements.runningContainer.classList.remove('hidden');
        }
        if (elements.infoText) {
            elements.infoText.textContent = `Running normally • Last updated: ${new Date().toLocaleTimeString()}`;
        }
    } else {
        if (elements.runningContainer) {
            elements.runningContainer.classList.add('hidden');
        }
        if (elements.errorContainer) {
            elements.errorContainer.classList.remove('hidden');
        }
    }
}

// Render Jobs
function renderJobs(jobsData: Job[]): void {
    jobs = jobsData || [];
    if (elements.jobsLoading) {
        elements.jobsLoading.classList.add('hidden');
    }

    if (jobs.length === 0) {
        if (elements.jobsList) {
            elements.jobsList.classList.add('hidden');
        }
        if (elements.noJobs) {
            elements.noJobs.classList.remove('hidden');
        }
        return;
    }

    if (elements.noJobs) {
        elements.noJobs.classList.add('hidden');
    }
    if (elements.jobsList) {
        elements.jobsList.classList.remove('hidden');
        elements.jobsList.innerHTML = jobs.map(job => createJobCard(job)).join('');
    }

    // Attach event listeners to new buttons
    document.querySelectorAll('.job-action-btn').forEach(btn => {
        btn.addEventListener('click', handleJobAction);
    });
}

function createJobCard(job: Job): string {
    const statusClass = getStatusClass(job);
    const nextRun = job.next_run ? new Date(job.next_run).toLocaleString() : 'Not scheduled';

    // Recent logs HTML
    let logsHtml = '';
    if (job.recent_logs && job.recent_logs.length > 0) {
        logsHtml = `
            <div class="mt-4 bg-gray-50 rounded border border-gray-200 overflow-hidden">
                <div class="px-3 py-1 bg-gray-100 text-xs font-semibold text-gray-500 border-b border-gray-200">
                    Recent Logs
                </div>
                <div class="max-h-32 overflow-y-auto">
                    ${job.recent_logs.map(log => `
                        <div class="log-entry ${getLogClass(log.level || '')}">
                            <span class="text-gray-400">[${new Date(log.timestamp).toLocaleTimeString()}]</span>
                            <span class="${getLogLevelColor(log.level || '')} font-bold">${log.level || 'INFO'}</span>: 
                            ${escapeHtml(log.message)}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Parameters HTML
    let paramsHtml = '';
    if (job.parameters && Object.keys(job.parameters).length > 0) {
        paramsHtml = `
            <div class="mt-4 parameter-form hidden" id="params-${job.id}">
                <h4 class="text-sm font-semibold mb-2">Run with Parameters</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    ${Object.entries(job.parameters).map(([key, desc]) => `
                        <div>
                            <label class="block text-xs font-medium text-gray-700 mb-1">${key}</label>
                            <input type="text" data-param="${key}" placeholder="${desc}" 
                                class="w-full text-sm border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 p-1">
                        </div>
                    `).join('')}
                </div>
                <div class="mt-3 flex justify-end">
                     <button class="text-xs text-gray-500 mr-2 hover:text-gray-700" onclick="toggleParams('${job.id}')">Cancel</button>
                     <button class="bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700" 
                        onclick="runJobWithParams('${job.id}', '${job.actual_job_id || job.id}')">
                        Run Now
                     </button>
                </div>
            </div>
        `;
    }

    return `
        <div class="job-card bg-white rounded-lg shadow p-6 border-l-4 ${getStatusBorderColor(job)} relative">
            <div class="flex justify-between items-start">
                <div>
                    <div class="flex items-center space-x-3">
                        <h3 class="text-lg font-bold text-gray-900">${job.name || job.id}</h3>
                        <span class="status-badge ${statusClass}">${getJobStatusLabel(job)}</span>
                    </div>
                    <p class="text-xs text-gray-500 mt-1 font-mono">${job.id}</p>
                    
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3 text-sm">
                        <div>
                            <span class="text-gray-500">Next Run:</span>
                            <span class="font-medium ${!job.next_run ? 'text-yellow-600' : 'text-gray-900'}">${nextRun}</span>
                        </div>
                        <div>
                            <span class="text-gray-500">Schedule:</span>
                            <span class="font-medium text-gray-900">${getScheduleText(job.trigger || '')}</span>
                        </div>
                    </div>
                </div>
                
                <div class="flex space-x-2">
                    ${job.next_run
            ? `<button class="job-action-btn text-yellow-600 hover:text-yellow-800 p-2" 
                                data-action="pause" data-id="${job.actual_job_id || job.id}" title="Pause Job">
                                <i class="fas fa-pause"></i>
                           </button>`
            : `<button class="job-action-btn text-green-600 hover:text-green-800 p-2" 
                                data-action="resume" data-id="${job.actual_job_id || job.id}" title="Resume Job">
                                <i class="fas fa-play"></i>
                           </button>`
        }
                    
                    ${Object.keys(job.parameters || {}).length > 0
            ? `<button class="text-blue-600 hover:text-blue-800 p-2" 
                                onclick="toggleParams('${job.id}')" title="Run with Parameters">
                                <i class="fas fa-cog"></i>
                           </button>`
            : `<button class="job-action-btn text-blue-600 hover:text-blue-800 p-2" 
                                data-action="run" data-id="${job.actual_job_id || job.id}" title="Run Now">
                                <i class="fas fa-bolt"></i>
                           </button>`
        }
                </div>
            </div>
            
            ${paramsHtml}
            ${logsHtml}
        </div>
    `;
}

// Helper Functions
function getStatusClass(job: Job): string {
    if (job.is_paused || !job.next_run) {
        return 'status-paused';
    }
    if (job.is_running) {
        return 'status-running';
    }
    if (job.last_error) {
        return 'status-failed';
    }
    return 'status-idle';
}

function getJobStatusLabel(job: Job): string {
    if (job.is_paused || !job.next_run) {
        return 'Paused';
    }
    if (job.is_running) {
        return 'Running';
    }
    if (job.last_error) {
        return 'Failed';
    }
    return 'Scheduled';
}

function getStatusBorderColor(job: Job): string {
    if (job.is_paused || !job.next_run) {
        return 'border-yellow-400';
    }
    if (job.last_error) {
        return 'border-red-500';
    }
    if (job.is_running) {
        return 'border-blue-500';
    }
    return 'border-green-500';
}

function getScheduleText(trigger: string): string {
    if (!trigger) {
        return 'Manual';
    }
    return trigger.replace('cron[', '').replace(']', '').replace('interval[', 'Every ');
}

function getLogClass(level: string): string {
    return level === 'ERROR' ? 'bg-red-50' : '';
}

function getLogLevelColor(level: string): string {
    if (level === 'ERROR') {
        return 'text-red-600';
    }
    if (level === 'WARNING') {
        return 'text-yellow-600';
    }
    return 'text-blue-600';
}

function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(msg: string): void {
    if (elements.errorMsg) {
        elements.errorMsg.classList.remove('hidden');
    }
    if (elements.errorText) {
        elements.errorText.textContent = msg;
    }
    setTimeout(() => {
        if (elements.errorMsg) {
            elements.errorMsg.classList.add('hidden');
        }
    }, 5000);
}

// Job Actions
async function handleJobAction(e: Event): Promise<void> {
    const btn = e.currentTarget as HTMLElement;
    const action = btn.getAttribute('data-action');
    const jobId = btn.getAttribute('data-id');

    if (!action || !jobId) {
        return;
    }

    // Visual feedback
    const originalIcon = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.setAttribute('disabled', 'true');

    try {
        const response = await fetch(`/api/jobs/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: jobId } as JobActionRequest)
        });

        const data: JobsApiResponse = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Action failed');
        }

        // Refresh immediately
        fetchStatus();

    } catch (error) {
        console.error('Job action error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        showError(errorMessage);
    } finally {
        btn.innerHTML = originalIcon;
        btn.removeAttribute('disabled');
    }
}

async function startScheduler(): Promise<void> {
    try {
        const response = await fetch('/api/jobs/start-scheduler', { method: 'POST' });
        const data: JobsApiResponse = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to start scheduler');
        }
        fetchStatus();
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        showError(errorMessage);
    }
}

// Global functions for inline onclick handlers
export function toggleParams(id: string): void {
    const el = document.getElementById(`params-${id}`);
    if (el) {
        el.classList.toggle('hidden');
    }
}

export async function runJobWithParams(id: string, actualJobId: string): Promise<void> {
    const container = document.getElementById(`params-${id}`);
    if (!container) {
        return;
    }

    const inputs = container.querySelectorAll<HTMLInputElement>('input');
    const params: Record<string, string> = {};

    inputs.forEach(input => {
        if (input.value.trim()) {
            const paramKey = input.getAttribute('data-param');
            if (paramKey) {
                params[paramKey] = input.value.trim();
            }
        }
    });

    try {
        const response = await fetch('/api/jobs/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: actualJobId, parameters: params } as JobActionRequest)
        });
        const data: JobsApiResponse = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to run job');
        }

        // Hide params and refresh
        toggleParams(id);
        fetchStatus();

    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        showError(errorMessage);
    }
}

// Make functions available globally for inline onclick handlers
declare global {
    interface Window {
        toggleParams: typeof toggleParams;
        runJobWithParams: typeof runJobWithParams;
    }
}

// Assign to window for inline handlers
window.toggleParams = toggleParams;
window.runJobWithParams = runJobWithParams;
