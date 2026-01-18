import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const body = await request.json();

        // Proxy logic
        const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

        const res = await fetch(`${backendUrl}/recommend`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            const errorText = await res.text();
            return NextResponse.json(
                { error: `Backend failed with ${res.status}`, details: errorText },
                { status: res.status }
            );
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("Proxy error:", error);
        return NextResponse.json(
            { error: 'Internal User Proxy Error' },
            { status: 500 }
        );
    }
}
