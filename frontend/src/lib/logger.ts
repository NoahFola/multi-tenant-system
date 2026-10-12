type LogLevel = "debug" | "info" | "warn" | "error";

const IS_DEV = import.meta.env.MODE === "development";

class Logger {
  private formatMessage(level: LogLevel, context: string, message: string, data?: any) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}] [${context}]`;
    return { prefix, message, data };
  }

  private sendToTerminal(level: LogLevel, prefix: string, msg: string, data?: any) {
    if (!IS_DEV) return;
    try {
      // Fire and forget to our custom Vite plugin endpoint
      fetch('/api/__log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level, prefix, msg, data })
      }).catch(() => {});
    } catch (e) {}
  }

  debug(context: string, message: string, data?: any) {
    if (!IS_DEV) return;
    const { prefix, message: msg, data: d } = this.formatMessage("debug", context, message, data);
    this.sendToTerminal("debug", prefix, msg, d);
    if (d) console.debug(`${prefix} ${msg}`, d);
    else console.debug(`${prefix} ${msg}`);
  }

  info(context: string, message: string, data?: any) {
    const { prefix, message: msg, data: d } = this.formatMessage("info", context, message, data);
    this.sendToTerminal("info", prefix, msg, d);
    if (d) console.info(`${prefix} ${msg}`, d);
    else console.info(`${prefix} ${msg}`);
  }

  warn(context: string, message: string, data?: any) {
    const { prefix, message: msg, data: d } = this.formatMessage("warn", context, message, data);
    this.sendToTerminal("warn", prefix, msg, d);
    if (d) console.warn(`${prefix} ${msg}`, d);
    else console.warn(`${prefix} ${msg}`);
  }

  error(context: string, message: string, error?: any) {
    const { prefix, message: msg, data: err } = this.formatMessage("error", context, message, error);
    this.sendToTerminal("error", prefix, msg, err);
    if (err) console.error(`${prefix} ${msg}`, err);
    else console.error(`${prefix} ${msg}`);
  }
}

export const logger = new Logger();
