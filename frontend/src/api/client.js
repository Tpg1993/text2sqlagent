export async function chat(message, onProgress) {
    // Generate session ID
    const sessionId = crypto.randomUUID();

    // Get token from storage
    const token = localStorage.getItem('token');

    // Connect to SSE stream for progress updates (best-effort; polling is the reliable fallback)
    let eventSource = null;
    if (onProgress) {
        const API_BASE_URL = '/api/v1';
        eventSource = new EventSource(`${API_BASE_URL}/stream/${sessionId}?token=${token}`);
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.event === 'progress') {
                    onProgress(data.data.message);
                } else if (data.event === 'approval_result') {
                    onProgress(data.data);
                }
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        };
        eventSource.onerror = () => {
            eventSource.close();
        };
    }

    const headers = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!response.ok) {
        if (eventSource) eventSource.close();

        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            const text = await response.text().catch(() => '');
            errorData = { error: text || 'Unknown Error' };
        }

        const backendMessage =
            errorData?.message ||
            errorData?.detail ||
            errorData?.error ||
            (Array.isArray(errorData?.detail) ? JSON.stringify(errorData.detail) : null);

        const error = new Error(backendMessage || `Request failed with status ${response.status}`);
        error.status = response.status;
        error.data = errorData;
        throw error;
    }

    const result = await response.json();

    // Close SSE connection only if NOT pending approval
    if (eventSource) {
        if (result.approval_status !== 'pending') {
            setTimeout(() => eventSource.close(), 100);
        } else {
            // Keep it open for best-effort SSE; polling will also cover this
            console.log("Keeping SSE open for approval (polling is also active)...");
        }
    }

    return result;
}

/**
 * Poll the approval status of a pending request.
 * Returns { status, results?, message? } from GET /api/v1/approval-status/{requestId}
 */
export async function pollApprovalStatus(requestId) {
    const token = localStorage.getItem('token');
    const response = await fetch(`/api/v1/approval-status/${requestId}`, {
        headers: {
            'Authorization': token ? `Bearer ${token}` : '',
        }
    });

    if (!response.ok) {
        const err = new Error(`Status check failed: ${response.status}`);
        err.status = response.status;
        throw err;
    }

    return await response.json();
}
