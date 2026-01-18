'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

interface ServerStatusContextType {
    isReady: boolean;
    statusMessage: string;
}

const ServerStatusContext = createContext<ServerStatusContextType>({
    isReady: false,
    statusMessage: 'Connecting...',
});

export const useServerStatus = () => useContext(ServerStatusContext);

export default function ServerStatusProvider({ children }: { children: React.ReactNode }) {
    const [isReady, setIsReady] = useState(false);
    const [statusMessage, setStatusMessage] = useState('Checking server status...');

    useEffect(() => {
        let intervalId: NodeJS.Timeout;

        const checkStatus = async () => {
            try {
                // Use default timeout (don't hang forever)
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);

                const res = await fetch('/api/health', {
                    signal: controller.signal,
                    cache: 'no-store'
                });
                clearTimeout(timeoutId);

                if (res.ok) {
                    const data = await res.json();
                    if (data.model_ready) {
                        setIsReady(true);
                        setStatusMessage('Server Ready');
                        return true; // Stop polling
                    } else {
                        setIsReady(false);
                        setStatusMessage('Waking up AI models (this takes ~30s)...');
                        return false;
                    }
                } else {
                    // 502 or 503 from Render during boot
                    setIsReady(false);
                    setStatusMessage('Server is booting up...');
                    return false;
                }
            } catch (error) {
                console.warn('Server ping failed', error);
                setIsReady(false);
                setStatusMessage('Connecting to server...');
                return false;
            }
        };

        // Initial check
        checkStatus();

        // Poll every 2 seconds until ready
        intervalId = setInterval(async () => {
            const ready = await checkStatus();
            if (ready) {
                clearInterval(intervalId);
            }
        }, 2000);

        return () => clearInterval(intervalId);
    }, []);

    return (
        <ServerStatusContext.Provider value={{ isReady, statusMessage }}>
            {/* Optional: Global Banner for cold start */}
            {!isReady && (
                <div className="bg-blue-600 text-white text-center text-sm py-2 px-4 transition-all duration-500 ease-in-out">
                    <span className="animate-pulse font-medium">🚀 {statusMessage}</span>
                </div>
            )}
            {children}
        </ServerStatusContext.Provider>
    );
}
