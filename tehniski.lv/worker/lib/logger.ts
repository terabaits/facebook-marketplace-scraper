const isJson = process.env.NODE_ENV === 'production';
function writeLog(level: string, msg: string, meta?: Record<string, unknown>) {
  const entry = { ts: new Date().toISOString(), level, msg, ...meta };
  if (isJson) console.log(JSON.stringify(entry));
  else console.log(`[${level}] ${msg}`, meta ?? '');
}
export const log = {
  info: (msg: string, meta?: Record<string, unknown>) => writeLog('info', msg, meta),
  warn: (msg: string, meta?: Record<string, unknown>) => writeLog('warn', msg, meta),
  error: (msg: string, meta?: Record<string, unknown>) => writeLog('error', msg, meta)
};
