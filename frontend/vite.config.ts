import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Custom plugin to receive browser logs and print them in the Vite terminal
const terminalLoggerPlugin = () => ({
  name: 'terminal-logger',
  configureServer(server: any) {
    server.middlewares.use('/api/__log', (req: any, res: any) => {
      if (req.method === 'POST') {
        let body = '';
        req.on('data', (chunk: any) => { body += chunk.toString() });
        req.on('end', () => {
          try {
            const { level, prefix, msg, data } = JSON.parse(body);

            // Basic ANSI color codes for the terminal
            const colors: Record<string, string> = {
              debug: '\x1b[90m', // gray
              info: '\x1b[36m',  // cyan
              warn: '\x1b[33m',  // yellow
              error: '\x1b[31m', // red
            };
            const reset = '\x1b[0m';
            const color = colors[level] || reset;

            const logMsg = `${color}${prefix} ${msg}${reset}`;

            if (data) {
              console.log(logMsg, JSON.stringify(data, null, 2));
            } else {
              console.log(logMsg);
            }
          } catch (e) { }
          res.end('ok');
        });
      } else {
        res.end('Method not allowed');
      }
    });
  }
});

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), terminalLoggerPlugin()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Proxy API requests to bypass CORS
    proxy: {
      '/auth': { target: 'http://localhost:8001', changeOrigin: true },
      '/users': { target: 'http://localhost:8002', changeOrigin: true },
      '/invitations': { target: 'http://localhost:8002', changeOrigin: true },
      '/projects': { target: 'http://localhost:8003', changeOrigin: true },
      '/workflows': { target: 'http://localhost:8003', changeOrigin: true },
      '/notifications': { target: 'http://localhost:8004', changeOrigin: true },
      '/audit-logs': { target: 'http://localhost:8005', changeOrigin: true },
    }
  }
})
