'use client';

import { useEffect } from 'react';

export default function WakeUpServer() {
    useEffect(() => {
        // Fire and forget - doesn't interfere with UI
        fetch('/api/health').catch(err => {
            console.warn('Backend wake-up ping failed:', err);
        });
    }, []);

    return null; // Component renders nothing
}
