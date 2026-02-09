export async function chat(message) {
    const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
    });

    if (!response.ok) {
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

    return response.json();
}
