import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    define: {
        // Fallback for gateway URL
        'import.meta.env.VITE_GATEWAY_URL': JSON.stringify(
            process.env.VITE_GATEWAY_URL || 'http://localhost:3000'
        ),
    },
})
