export async function chat(message, onProgress) {
    // Generate session ID
    const sessionId = crypto.randomUUID();

    // Get token from storage
    const token = localStorage.getItem('token');

    // Connect to SSE stream for progress updates
    let eventSource = null;
    if (onProgress) {
        const API_BASE_URL = '/api/v1'; // Assuming this base URL based on existing code
        eventSource = new EventSource(`${API_BASE_URL}/stream/${sessionId}?token=${token}`);
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.event === 'progress') {
                    onProgress(data.data.message);
                } else if (data.event === 'approval_result') {
                    onProgress(data.data); // Reuse callback or add new one?
                    // Better to pass whole object so UI can distinguish
                }
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        };
        eventSource.onerror = () => {
            eventSource.close();
        };
    }

    // Token already retrieved above
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

    // Close SSE connection
    // Close SSE connection only if NOT pending approval
    if (eventSource) {
        if (result.approval_status !== 'pending') {
            setTimeout(() => eventSource.close(), 100);
        } else {
            // Keep it open for approval result
            console.log("Keeping SSE open for approval...");
        }
    }

    return result;
}
