export async function chat(message, onProgress) {
    // Generate session ID
    const sessionId = crypto.randomUUID();

    // Connect to SSE stream for progress updates
    let eventSource = null;
    if (onProgress) {
        eventSource = new EventSource(`/api/v1/stream/${sessionId}`);
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.event === 'progress') {
                    onProgress(data.data.message);
                }
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        };
        eventSource.onerror = () => {
            eventSource.close();
        };
    }

    const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!response.ok) {
        if (eventSource) eventSource.close();

        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            errorData = { error: 'Unknown Error' };
        }

        const error = new Error(errorData.message || 'Network response was not ok');
        error.status = response.status;
        error.data = errorData;
        throw error;
    }

    const result = await response.json();

    // Close SSE connection
    if (eventSource) {
        setTimeout(() => eventSource.close(), 100);
    }

    return result;
}
